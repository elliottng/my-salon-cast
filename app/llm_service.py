# app/llm_service.py

import google.generativeai as genai
import os
import json
import re
import logging
import functools
from datetime import datetime
from typing import Dict, List, Optional, Any, Union, Tuple
import asyncio

from dotenv import load_dotenv
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type
from google.api_core.exceptions import (
    DeadlineExceeded,
    ServiceUnavailable,
    ResourceExhausted,
    InternalServerError
)
from google.ai.generativelanguage_v1beta.types import GenerationConfig
from pydantic import ValidationError

from .podcast_models import PersonaResearch, PodcastOutline, DialogueTurn, SourceAnalysis, OutlineSegment
from .common_exceptions import LLMProcessingError

# Configure logger
logger = logging.getLogger(__name__)
# Basic configuration, can be adjusted based on project-wide logging setup
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')

class LLMNotInitializedError(ValueError):
    """Custom exception for LLM service initialization errors."""
    pass

class GeminiService:
    @staticmethod
    def _clean_keys_recursive(obj):
        # logger.debug(f"_clean_keys_recursive processing type: {type(obj)}")
        if isinstance(obj, dict):
            new_dict = {}
            for key, value in obj.items():
                stripped_key = key.strip()
                # logger.debug(f"Original key: '{key}', Stripped key: '{stripped_key}'")
                new_dict[stripped_key] = GeminiService._clean_keys_recursive(value)
            return new_dict
        elif isinstance(obj, list):
            return [GeminiService._clean_keys_recursive(element) for element in obj]
        return obj

    def __init__(self, api_key: str = None):
        """
        Initializes the Gemini Service.
        API key is read from GOOGLE_API_KEY environment variable if not provided.
        """
        load_dotenv() # Load environment variables from .env file
        
        if api_key is None:
            api_key = os.getenv("GOOGLE_API_KEY")
            
        if not api_key:
            raise LLMNotInitializedError("API key for Gemini service is required. Set GOOGLE_API_KEY environment variable or pass it directly.")
        
        genai.configure(api_key=api_key)
        # Using gemini-1.5-pro-latest as per discussion.
        # Consider making the model name configurable if needed in the future.
        self.model = genai.GenerativeModel('gemini-1.5-pro-latest')

    @retry(
        stop=stop_after_attempt(3),  # Retry up to 3 times (total of 4 attempts)
        wait=wait_exponential(multiplier=1, min=2, max=10),  # Wait 2s, then 4s, then 8s
        retry=retry_if_exception_type((
            DeadlineExceeded,       # e.g., 504 Gateway Timeout
            ServiceUnavailable,     # e.g., 503 Service Unavailable
            ResourceExhausted,      # e.g., 429 Rate Limiting / Quota issues
            InternalServerError     # e.g., 500 Internal Server Error
        )),
        before_sleep=lambda retry_state: logger.warning(
            f"Retrying API call to Gemini due to {retry_state.outcome.exception().__class__.__name__} "
            f"(Reason: {retry_state.outcome.exception()}). Attempt #{retry_state.attempt_number}"
        )
    )
    async def generate_text_async(self, prompt: str, timeout_seconds: int = 60) -> str:
        """
        Asynchronously generates text based on the given prompt using the configured Gemini model.
        
        Args:
            prompt: The prompt to send to the model
            timeout_seconds: Maximum time to wait for the API call in seconds (default: 30)
            
        Returns:
            The generated text response
            
        Raises:
            TimeoutError: If the API call exceeds the timeout_seconds
            ValueError: If the prompt is empty
            RuntimeError: For other unexpected errors
        """
        logger.info("ENTRY: generate_text_async method called")
        logger.info(f"Prompt length: {len(prompt) if prompt else 0} characters with {timeout_seconds}s timeout")
        
        if not prompt:
            logger.error("Prompt cannot be empty.")
            raise ValueError("Prompt cannot be empty.")
            
        try:
            # Use asyncio.wait_for to add a timeout to the thread call
            logger.info(f"Calling Gemini model generate_content with {timeout_seconds}s timeout")
            
            # Create a task with asyncio.to_thread and apply a timeout
            task = asyncio.create_task(asyncio.to_thread(self.model.generate_content, prompt))
            
            # Wait for the task with a timeout
            try:
                response = await asyncio.wait_for(task, timeout=timeout_seconds)
                logger.info(f"API call completed successfully within {timeout_seconds}s timeout")
            except asyncio.TimeoutError:
                logger.error(f"API call timed out after {timeout_seconds} seconds")
                task.cancel()
                # Try to get the task result, but don't wait - just to see if there's an exception
                try:
                    task.result()
                except Exception as task_ex:
                    logger.error(f"Task had exception: {task_ex}")
                error_json = '{"error": "Gemini API timeout", "details": "API call timed out after ' + str(timeout_seconds) + ' seconds"}'
                logger.error(f"Returning error JSON: {error_json}")
                return error_json
            
            # Check for response.parts for potentially multi-part responses
            if response.parts:
                logger.info(f"Response has {len(response.parts)} parts")
                # Ensure all parts are concatenated, checking if they have a 'text' attribute
                result = "".join(part.text for part in response.parts if hasattr(part, 'text'))
                logger.info(f"Concatenated response text length: {len(result)} characters")
                logger.info("EXIT: generate_text_async completed successfully with multi-part response")
                return result
            # Fallback if response.text is directly available (older API versions or simpler responses)
            elif hasattr(response, 'text') and response.text:
                logger.info(f"Response has single text attribute of length: {len(response.text)} characters")
                logger.info("EXIT: generate_text_async completed successfully with single-part response")
                return response.text
            else:
                # This case might occur if the response is blocked, has no text content, or an unexpected structure
                logger.warning("No text content found in response")
                # Check for prompt feedback which might indicate blocking
                if hasattr(response, 'prompt_feedback') and response.prompt_feedback:
                    logger.warning(f"Response has prompt_feedback: {response.prompt_feedback}")
                    logger.info("EXIT: generate_text_async with prompt feedback issue")
                    return f"Error: Could not generate text. Prompt feedback: {response.prompt_feedback}"
                logger.warning("No text content or prompt feedback found in response")
                logger.info("EXIT: generate_text_async with empty/blocked response")
                return "Error: No text content in Gemini response or response was blocked."

        except Exception as e:
            # This is a general catch-all for any other errors during the API call or response processing.
            logger.error(f"Unexpected error in generate_text_async: {e.__class__.__name__} - {e}", exc_info=True)
            logger.info("EXIT: generate_text_async with exception")
            # Ensure an exception is raised so the caller knows something went wrong.
            raise RuntimeError(f"Failed to generate text due to an unexpected error: {e}") from e

    async def analyze_source_text_async(self, source_text: str, analysis_instructions: str = None) -> str:
        """
        Analyzes the provided source text using the LLM.
        Allows for custom analysis instructions.
        """
        logger.info("ENTRY: analyze_source_text_async method called")
        logger.info(f"Source text length: {len(source_text) if source_text else 0} characters")
        
        try:
            if not source_text:
                logger.error("Source text for analysis is empty or None")
                raise ValueError("Source text for analysis cannot be empty.")

            if analysis_instructions:
                logger.info(f"Using custom analysis instructions: {analysis_instructions[:100]}...")
                prompt = f"{analysis_instructions}\n\nAnalyze the following text:\n\n---\n{source_text}\n---"
            else:
                logger.info("Using default analysis prompt template")
                # Default analysis prompt
                prompt = (
                    "Please analyze the following text. Identify the key topics, main arguments, "
                    "the overall sentiment, and any notable stylistic features. "
                    "Provide a concise summary of your analysis.\n\n"
                    f"---\n{source_text}\n---"
                )
        
            logger.info(f"Constructed prompt of length {len(prompt)} characters")
            logger.info("Calling generate_text_async for source analysis...")
            
            try:
                response = await self.generate_text_async(prompt)
                logger.info(f"generate_text_async returned response of length: {len(response) if response else 0} characters")
                
                if not response:
                    logger.error("LLM returned empty response for source analysis")
                    return '{"error": "LLM returned empty response", "raw_response": ""}'
                
                # Try to validate if the response is a proper JSON format
                try:
                    import json
                    json.loads(response)  # Just check if it's valid JSON
                    logger.info("Response appears to be valid JSON")
                except json.JSONDecodeError:
                    logger.warning("Response is not valid JSON, it may be a plain text response")
                    logger.warning(f"First 200 chars of response: {response[:200]}")
                    # We'll let the calling code handle this situation
                
                logger.info("EXIT: analyze_source_text_async completed successfully")
                return response
                
            except Exception as gen_error:
                logger.error(f"Error during generate_text_async call: {gen_error}", exc_info=True)
                error_msg = str(gen_error).replace('"', '\\"')
                error_json = '{"error": "LLM API error: ' + error_msg + '", "raw_response": ""}'
                logger.error(f"Returning error JSON: {error_json}")
                return error_json
                
        except ValueError as ve:
            logger.error(f"ValueError in analyze_source_text_async: {ve}")
            error_msg = str(ve).replace('"', '\\"')
            return '{"error": "ValueError: ' + error_msg + '", "raw_response": ""}'
            
        except Exception as e:
            logger.error(f"Unexpected error in analyze_source_text_async: {e}", exc_info=True)
            error_msg = str(e).replace('"', '\\"')
            return '{"error": "Unexpected error: ' + error_msg + '", "raw_response": ""}'
            
        finally:
            logger.info("EXIT: analyze_source_text_async method (in finally block)")

    async def research_persona_async(self, source_text: str, person_name: str) -> PersonaResearch:
        """
        Conducts persona research based on the provided source text.
        Allows for specifying a focus for the persona research.
        """
        if not source_text:
            raise ValueError("Source text for persona research cannot be empty.")
        if not person_name:
            raise ValueError("Person name for persona research cannot be empty.")

        # Create a simple person_id from the name (e.g., for filenames or internal references)
        # This can be made more robust if needed (e.g., handling special characters, ensuring uniqueness)
        person_id = person_name.lower().replace(' ', '_').replace('.', '')

        prompt = f"""
Given the following source text, conduct detailed persona research for the individual named: '{person_name}'.

Source Text:
---
{source_text}
---

Please provide your research as a JSON object with the following structure and fields:
{{
  "person_id": "{person_id}",
  "name": "{person_name}",
  "viewpoints": ["List of key viewpoints, opinions, or arguments associated with {person_name} from the source text. Be specific and quote or paraphrase where possible."],
  "speaking_style": "Describe the observed or inferred speaking style of {person_name} (e.g., 'analytical and data-driven', 'passionate and persuasive', 'cautious and measured', 'storytelling and anecdotal'). Provide examples if possible.",
  "key_quotes": ["List direct memorable quotes from {person_name} found in the source text. If no direct quotes are prominent, this can be an empty list or null."]
}}

Ensure the output is a single, valid JSON object only, with no additional text before or after the JSON.
"""

        json_response_str: str = None  # Initialize
        try:
            logger.info(f"Generating persona research for '{person_name}' with prompt (first 200 chars): {prompt[:200]}...")
            json_response_str = await self.generate_text_async(prompt)
            
            logger.debug(f"Raw LLM response for persona research of '{person_name}': {json_response_str}")

            # Strip potential markdown backticks if present
            if isinstance(json_response_str, str):
                # More robust stripping
                temp_str = json_response_str.strip() # Remove leading/trailing whitespace first
                if temp_str.startswith("```json") and temp_str.endswith("```"):
                    # Find the first newline after ```json
                    # The '7' comes from len("```json") + 1 for the newline, or just after ```json
                    # Correct start index for content after "```json\n" or "```json "
                    content_start_idx = temp_str.find('\n', 7) # Search after "```json"
                    if content_start_idx == -1: # if no newline after ```json, maybe it's just ```json{...}```
                        content_start_idx = 7 # len("```json")
                    else:
                        content_start_idx += 1 # move past the newline itself
                    
                    # Find the last occurrence of ``` to mark the end of the JSON content
                    content_end_idx = temp_str.rfind("```")
                    
                    if content_start_idx < content_end_idx:
                        json_content_candidate = temp_str[content_start_idx:content_end_idx]
                        json_response_str = json_content_candidate.strip() # Clean the extracted content
                    else: # Fallback if stripping logic is confused, try to use the original temp_str or log error
                        logger.warning(f"Markdown stripping for '```json...```' might have failed for '{person_name}'. Using temp_str directly after outer strip.")
                        json_response_str = temp_str # Or consider it an error

                elif temp_str.startswith("```") and temp_str.endswith("```"):
                    json_content_candidate = temp_str[3:-3]
                    json_response_str = json_content_candidate.strip()
                # If no markdown fences, or they were already stripped,
                # ensure json_response_str is still the potentially valid JSON string
                else:
                    json_response_str = temp_str # Use the stripped version if no fences matched
        
            # Add a log to see what exactly is being passed to json.loads
            logger.debug(f"String to be parsed by json.loads for '{person_name}': '{json_response_str}'")
            cleaned_response_text = self._clean_llm_json_response(json_response_str)
            logger.debug(f"Cleaned persona research response: {cleaned_response_text[:200]}...")
            
            parsed_json = json.loads(cleaned_response_text)
            parsed_json = GeminiService._clean_keys_recursive(parsed_json) # Clean keys before validation
            logger.debug(f"Attempting to create PersonaResearch with (cleaned) keys: {list(parsed_json.keys()) if isinstance(parsed_json, dict) else 'Not a dict'}")
            persona_research_data = PersonaResearch(**parsed_json)
            logger.info(f"Successfully parsed and validated persona research for '{person_name}'.")
            return persona_research_data

        except json.JSONDecodeError as e:
            output_for_log = str(json_response_str)[:500] if isinstance(json_response_str, str) else "LLM output not available or not a string"
            logger.error(f"JSONDecodeError parsing persona research for '{person_name}': {e}. LLM Output: {output_for_log}", exc_info=True)
            raise ValueError(f"Failed to parse LLM response as JSON for persona '{person_name}'.") from e
        except ValidationError as e: 
            output_for_log = str(json_response_str)[:500] if isinstance(json_response_str, str) else "LLM output not available or not a string"
            logger.error(f"ValidationError validating persona research for '{person_name}': {e}. LLM Output: {output_for_log}", exc_info=True)
            raise ValueError(f"LLM response for persona '{person_name}' did not match expected structure.") from e
        except Exception as e: # Catches errors from generate_text_async, or other unexpected issues like TypeError if json_response_str was None and json.loads tried it.
            output_for_log = str(json_response_str)[:500] if isinstance(json_response_str, str) else "LLM output not available or not a string"
            logger.error(f"Unexpected error during persona research for '{person_name}': {e.__class__.__name__} - {e}. LLM Output was: {output_for_log}", exc_info=True)
            raise RuntimeError(f"An unexpected error occurred while researching persona '{person_name}'.") from e

    def _parse_duration_to_seconds(self, duration_str: str) -> int:
        """
        Parse a duration string like "5 minutes" or "2 mins" into seconds.
        Returns default of 300 seconds (5 minutes) if parsing fails.
        """
        try:
            # Extract numeric part and convert to float
            numeric_part = float(re.search(r'\d+(?:\.\d+)?', duration_str).group())
            
            # Determine the unit (default to minutes)
            if re.search(r'hour|hr', duration_str, re.IGNORECASE):
                return int(numeric_part * 3600)  # hours to seconds
            elif re.search(r'sec|second', duration_str, re.IGNORECASE):
                return int(numeric_part)  # already in seconds
            else:  # Default to minutes
                return int(numeric_part * 60)  # minutes to seconds
        except (AttributeError, ValueError):
            logger.warning(f"Could not parse duration: {duration_str}. Using default of 300 seconds.")
            return 300  # Default to 5 minutes
    
    def _validate_and_adjust_segments(self, podcast_outline: PodcastOutline, total_duration_seconds: int) -> PodcastOutline:
        """
        Validate and adjust segment durations to match the desired podcast length.
        Also ensures proper structure with intro, main body segments, and conclusion.
        """
        segments = podcast_outline.segments
        
        # 1. Check if we have segments
        if not segments:
            logger.warning("No segments in podcast outline. Creating basic structure.")
            return self._create_fallback_outline(podcast_outline.title_suggestion, 
                                               podcast_outline.summary_suggestion, 
                                               total_duration_seconds)
        
        # 2. Validate segment IDs and ensure they're unique
        segment_ids = [s.segment_id for s in segments]
        if len(segment_ids) != len(set(segment_ids)):
            logger.warning("Duplicate segment IDs found. Assigning new unique IDs.")
            for i, segment in enumerate(segments):
                segment.segment_id = f"segment_{i+1}"
        
        # 3. Assign durations if missing or zero
        segments_with_duration = [s for s in segments if s.estimated_duration_seconds and s.estimated_duration_seconds > 0]
        segments_without_duration = [s for s in segments if not s.estimated_duration_seconds or s.estimated_duration_seconds <= 0]
        
        # If no segments have durations, distribute time based on ideal proportions
        if not segments_with_duration:
            logger.info("No segments have durations. Distributing time based on ideal proportions.")
            return self._distribute_time_to_segments(segments, total_duration_seconds)
        
        # 4. If some segments have durations but others don't, distribute remaining time
        if segments_without_duration:
            total_assigned_duration = sum(s.estimated_duration_seconds for s in segments_with_duration)
            remaining_duration = max(0, total_duration_seconds - total_assigned_duration)
            
            if remaining_duration > 0:
                per_segment_remaining = remaining_duration // len(segments_without_duration)
                for segment in segments_without_duration:
                    segment.estimated_duration_seconds = per_segment_remaining
            else:
                # Not enough time left, scale everything down
                scaling_factor = total_duration_seconds / total_assigned_duration
                for segment in segments_with_duration:
                    segment.estimated_duration_seconds = int(segment.estimated_duration_seconds * scaling_factor)
                for segment in segments_without_duration:
                    segment.estimated_duration_seconds = 10  # Minimal duration
        
        # 5. If total duration doesn't match target, scale proportionally
        total_segment_duration = sum(s.estimated_duration_seconds for s in segments)
        if abs(total_segment_duration - total_duration_seconds) > 30:  # Allow 30 second margin
            scaling_factor = total_duration_seconds / total_segment_duration
            for segment in segments:
                segment.estimated_duration_seconds = max(10, int(segment.estimated_duration_seconds * scaling_factor))
        
        # 6. Validate structure (intro, body, conclusion)
        has_intro = any("intro" in s.segment_id.lower() or "introduction" in s.segment_title.lower() for s in segments)
        has_conclusion = any("conclu" in s.segment_id.lower() or "conclusion" in s.segment_title.lower() 
                            or "outro" in s.segment_id.lower() or "summary" in s.segment_title.lower() for s in segments)
        
        if not (has_intro and has_conclusion):
            logger.warning("Missing intro or conclusion segments. Restructuring outline.")
            return self._restructure_outline_segments(podcast_outline, total_duration_seconds)
        
        return podcast_outline
    
    def _distribute_time_to_segments(self, segments: List[OutlineSegment], total_duration_seconds: int) -> PodcastOutline:
        """
        Distribute time to segments based on ideal proportions:
        - Intro: ~10-15% 
        - Body: ~70-80%
        - Conclusion: ~10-15%
        """
        intro_segments = []
        body_segments = []
        conclusion_segments = []
        
        # Categorize segments
        for segment in segments:
            if "intro" in segment.segment_id.lower() or "introduction" in segment.segment_title.lower():
                intro_segments.append(segment)
            elif "conclu" in segment.segment_id.lower() or "conclusion" in segment.segment_title.lower() \
                or "outro" in segment.segment_id.lower() or "summary" in segment.segment_title.lower():
                conclusion_segments.append(segment)
            else:
                body_segments.append(segment)
        
        # If categorization failed, make a best guess based on position
        if not intro_segments and not conclusion_segments and len(segments) >= 3:
            intro_segments = [segments[0]]
            conclusion_segments = [segments[-1]]
            body_segments = segments[1:-1]
        elif not intro_segments and not conclusion_segments and len(segments) == 2:
            intro_segments = [segments[0]]
            conclusion_segments = [segments[1]]
            body_segments = []
        elif not body_segments:
            # Create at least one body segment if none exist
            body_segments = [OutlineSegment(
                segment_id="body_1",
                segment_title="Main Discussion",
                speaker_id="Host",
                content_cue="Discuss the main points from the source material.",
                estimated_duration_seconds=0
            )]
        
        # Calculate ideal durations based on proportions
        intro_duration = int(total_duration_seconds * 0.15)  # 15%
        conclusion_duration = int(total_duration_seconds * 0.15)  # 15%
        body_duration = total_duration_seconds - intro_duration - conclusion_duration  # 70%
        
        # Distribute durations within each category
        if intro_segments:
            per_intro_segment = intro_duration // len(intro_segments)
            for segment in intro_segments:
                segment.estimated_duration_seconds = per_intro_segment
        
        if body_segments:
            per_body_segment = body_duration // len(body_segments)
            for segment in body_segments:
                segment.estimated_duration_seconds = per_body_segment
        
        if conclusion_segments:
            per_conclusion_segment = conclusion_duration // len(conclusion_segments)
            for segment in conclusion_segments:
                segment.estimated_duration_seconds = per_conclusion_segment
        
        # Recombine segments in proper order
        all_segments = intro_segments + body_segments + conclusion_segments
        
        # Create updated outline with the same title/summary but adjusted segments
        return PodcastOutline(
            title_suggestion=segments[0].segment_title if segments else "Generated Podcast",
            summary_suggestion="A podcast discussing the provided content.",
            segments=all_segments
        )
    
    def _restructure_outline_segments(self, podcast_outline: PodcastOutline, total_duration_seconds: int) -> PodcastOutline:
        """
        Restructure outline to ensure it has intro, body, and conclusion segments
        while preserving as much original content as possible.
        """
        original_segments = podcast_outline.segments
        
        # Check if we can identify intro, body, conclusion based on position
        if len(original_segments) >= 3:
            # Assume first segment is intro, last is conclusion, rest are body
            intro_segment = original_segments[0]
            intro_segment.segment_id = "intro_1"
            if "intro" not in intro_segment.segment_title.lower():
                intro_segment.segment_title = "Introduction: " + intro_segment.segment_title
            
            conclusion_segment = original_segments[-1]
            conclusion_segment.segment_id = "conclusion_1"
            if "conclu" not in conclusion_segment.segment_title.lower() and "summary" not in conclusion_segment.segment_title.lower():
                conclusion_segment.segment_title = "Conclusion: " + conclusion_segment.segment_title
                
            body_segments = original_segments[1:-1]
            for i, segment in enumerate(body_segments):
                segment.segment_id = f"body_{i+1}"
                
            # Calculate durations
            intro_duration = int(total_duration_seconds * 0.15)
            conclusion_duration = int(total_duration_seconds * 0.15)
            body_duration = total_duration_seconds - intro_duration - conclusion_duration
            
            intro_segment.estimated_duration_seconds = intro_duration
            conclusion_segment.estimated_duration_seconds = conclusion_duration
            
            if body_segments:
                per_body_segment = body_duration // len(body_segments)
                for segment in body_segments:
                    segment.estimated_duration_seconds = per_body_segment
            
            restructured_segments = [intro_segment] + body_segments + [conclusion_segment]
            
        else:
            # Not enough segments, need to create a proper structure
            restructured_segments = []
            
            # Create intro segment (preserve original if possible)
            if original_segments and len(original_segments) > 0:
                intro_segment = original_segments[0]
                intro_segment.segment_id = "intro_1"
                if "intro" not in intro_segment.segment_title.lower():
                    intro_segment.segment_title = "Introduction: " + intro_segment.segment_title
            else:
                intro_segment = OutlineSegment(
                    segment_id="intro_1",
                    segment_title="Introduction",
                    speaker_id="Host",
                    content_cue="Introduce the topic and speakers.",
                    estimated_duration_seconds=int(total_duration_seconds * 0.15)
                )
            restructured_segments.append(intro_segment)
            
            # Create body segment(s)
            if len(original_segments) > 1:
                # Use middle segment(s) as body
                body_segments = original_segments[1:] if len(original_segments) == 2 else original_segments[1:-1]
                for i, segment in enumerate(body_segments):
                    segment.segment_id = f"body_{i+1}"
                restructured_segments.extend(body_segments)
            else:
                # Create a new body segment
                body_segment = OutlineSegment(
                    segment_id="body_1",
                    segment_title="Main Discussion",
                    speaker_id="Host",
                    content_cue="Discuss the main points from the source material.",
                    estimated_duration_seconds=int(total_duration_seconds * 0.7)
                )
                restructured_segments.append(body_segment)
            
            # Create conclusion segment
            if len(original_segments) > 2:
                conclusion_segment = original_segments[-1]
                conclusion_segment.segment_id = "conclusion_1"
                if "conclu" not in conclusion_segment.segment_title.lower() and "summary" not in conclusion_segment.segment_title.lower():
                    conclusion_segment.segment_title = "Conclusion: " + conclusion_segment.segment_title
            else:
                conclusion_segment = OutlineSegment(
                    segment_id="conclusion_1",
                    segment_title="Conclusion",
                    speaker_id="Host",
                    content_cue="Summarize the key points and conclude the discussion.",
                    estimated_duration_seconds=int(total_duration_seconds * 0.15)
                )
            restructured_segments.append(conclusion_segment)
            
        return PodcastOutline(
            title_suggestion=podcast_outline.title_suggestion,
            summary_suggestion=podcast_outline.summary_suggestion,
            segments=restructured_segments
        )
    
    def _create_fallback_outline(self, title: str, summary: str, total_duration_seconds: int) -> PodcastOutline:
        """
        Create a fallback outline with standard intro, body, conclusion structure
        when the LLM doesn't provide valid segments.
        """
        intro_duration = int(total_duration_seconds * 0.15)  # 15%
        body_duration = int(total_duration_seconds * 0.7)   # 70%
        conclusion_duration = total_duration_seconds - intro_duration - body_duration  # 15%
        
        segments = [
            OutlineSegment(
                segment_id="intro_1",
                segment_title="Introduction",
                speaker_id="Host",
                content_cue="Introduce the topic and speakers.",
                estimated_duration_seconds=intro_duration
            ),
            OutlineSegment(
                segment_id="body_1",
                segment_title="Main Discussion",
                speaker_id="Host",
                content_cue="Discuss the main points from the source material.",
                estimated_duration_seconds=body_duration
            ),
            OutlineSegment(
                segment_id="conclusion_1",
                segment_title="Conclusion",
                speaker_id="Host",
                content_cue="Summarize the key points and conclude the discussion.",
                estimated_duration_seconds=conclusion_duration
            )
        ]
        
        return PodcastOutline(
            title_suggestion=title if title else "Generated Podcast",
            summary_suggestion=summary if summary else "A podcast discussing the provided content.",
            segments=segments
        )
    
    async def generate_podcast_outline_async(
        self,
        source_analyses: list[str],
        persona_research_docs: list[str],
        desired_podcast_length_str: str,
        num_prominent_persons: int,
        names_prominent_persons_list: list[str],
        user_provided_custom_prompt: str = None
    ) -> PodcastOutline:
        """
        Generates a podcast outline based on source analyses, persona research,
        and other parameters, using a detailed PRD-defined prompt or a user-provided custom prompt.
        """
        if not source_analyses:
            raise ValueError("At least one source analysis document is required.")

        final_prompt: str
        if user_provided_custom_prompt:
            # If user provides a custom prompt, we use it directly.
            # Consider if/how to append standard context if the custom prompt expects it.
            # For now, assuming custom prompt is self-contained or user includes placeholders.
            final_prompt = user_provided_custom_prompt
            # Example of appending context if needed:
            # context_parts = ["### Supporting Context ###"]
            # if source_analyses:
            #     for i, doc in enumerate(source_analyses):
            #         context_parts.append(f"Source Analysis Document {i+1}:\\n{doc}\\n---")
            # if persona_research_docs:
            #     for i, doc in enumerate(persona_research_docs):
            #         context_parts.append(f"Persona Research Document {i+1}:\\n{doc}\\n---")
            # formatted_context = "\\n".join(context_parts)
            # final_prompt += f"\\n\\n--- Supporting Context ---\\n{formatted_context}"
        else:
            # Format Source Analyses for PRD prompt
            formatted_source_analyses_str_parts = []
            if source_analyses:
                for i, doc in enumerate(source_analyses):
                    formatted_source_analyses_str_parts.append(f"Source Analysis Document {i+1}:\\n{doc}\\n---")
            else:
                formatted_source_analyses_str_parts.append("No source analysis documents provided.")
            input_formatted_source_analyses_str = "\n".join(formatted_source_analyses_str_parts)
            
            # Format Persona Research Documents for PRD prompt
            formatted_persona_research_str_parts = []
            if persona_research_docs:
                for i, doc in enumerate(persona_research_docs):
                    formatted_persona_research_str_parts.append(f"Persona Research Document {i+1}:\\n{doc}\\n---")
            else:
                formatted_persona_research_str_parts.append("No persona research documents provided.")
            input_formatted_persona_research_str = "\n".join(formatted_persona_research_str_parts)

            # Format Names of Prominent Persons for PRD prompt
            formatted_names_prominent_persons_str: str
            if names_prominent_persons_list:
                formatted_names_prominent_persons_str = ", ".join(names_prominent_persons_list)
            else:
                formatted_names_prominent_persons_str = "None"

            # PRD 4.2.4 Prompt Template with enhanced duration guidance
            prd_outline_prompt_template = """LLM Prompt: Podcast Outline Generation
Role: You are an expert podcast script developer and debate moderator. Your primary objective is to create a comprehensive, engaging, and informative podcast outline based on the provided materials.

Overall Podcast Goals:

Educate: Clearly summarize and explain the key topics, findings, and information presented in the source documents for an audience of intellectually curious professionals.
Explore Perspectives: If prominent persons are specified, the podcast must clearly articulate their known viewpoints and perspectives on the topics, drawing from their provided persona research documents.
Facilitate Insightful Discussion/Debate: If these prominent persons have differing opinions, or if source materials present conflicting yet important viewpoints, the podcast should feature a healthy, robust debate and discussion, allowing for strong expression of these differing standpoints.
Create Properly Timed Segments: Ensure the podcast fits within the requested duration by creating segments with appropriate estimated_duration_seconds values that sum up to the total requested length.

Inputs Provided to You:

Source Analysis Documents:
{input_formatted_source_analyses_str}

Persona Research Documents:
{input_formatted_persona_research_str}

Desired Podcast Length: {input_desired_podcast_length_str}
Number of Prominent Persons Specified: {input_num_prominent_persons}
Names of Prominent People Specified: {input_formatted_names_prominent_persons_str}

Task: Generate a Podcast Outline

Create a detailed outline that structures the podcast. The outline should serve as a blueprint for the subsequent dialogue writing step.

Outline Structure Requirements:

Your outline must include the following sections, with specific content tailored to the inputs:

I. Introduction (Approx. 10-15% of podcast length)
A.  Opening Hook: Suggest a compelling question or statement to grab the listener's attention, related to the core topic.
B.  Topic Overview: Briefly introduce the main subject(s) to be discussed, derived from the source analyses.
C.  Speaker Introduction:
* If prominent persons are specified (based on "Names of Prominent People Specified"): Introduce them by name (e.g., "Today, we'll explore these topics through the synthesized perspectives of [Name of Persona A] and [Name of Persona B]..."). Indicate their general relevance or contrasting viewpoints if immediately obvious.
* If no persons are specified: Plan for a "Host" and an "Analyst/Expert" or similar generic roles.

II. Main Body Discussion Segments (Approx. 70-80% of podcast length)
* Divide the main body into 2-4 distinct thematic segments.
* For each segment:
1.  Theme/Topic Identification: Clearly state the specific theme or key question this segment will address (derived from source analyses).
2.  Core Information Summary: Outline the key facts, data, or educational points from the source documents that need to be explained to the listener regarding this theme.
3.  Persona Integration & Discussion (if prominent persons are specified):
a.  Initial Viewpoints: Plan how each named persona will introduce their perspective or initial thoughts on this theme, drawing from their corresponding persona research document.
b.  Points of Alignment/Conflict: Identify if this theme highlights agreement or disagreement between the named personas, or between a persona and the source material, or conflicting information between sources.
c.  Structuring Debate (if conflict/disagreement is identified):
* Outline a sequence for named personas to strongly express their differing viewpoints.
* Suggest moments for direct engagement (e.g., "[Name of Persona A] challenges [Name of Persona B]'s point on X by stating Y," or "How does [Name of Persona A]'s view reconcile with Source Document 2's finding on Z?").
* Ensure the debate remains constructive and focused on elucidating the topic for the listener.
d.  Supporting Evidence: Note key pieces of information or brief quotes from the source analysis documents that personas should reference to support their arguments or that the narrator should use for clarification.
4.  Presenting Conflicting Source Information (if no personas, or if relevant beyond persona debate): If the source documents themselves contain important conflicting information on this theme, outline how this will be presented and explored.

III. Conclusion (Approx. 10-15% of podcast length)
A.  Summary of Key Takeaways: Briefly recap the main educational points and the core arguments/perspectives discussed.
B.  Final Persona Thoughts (if prominent persons specified): Allow a brief concluding remark from each named persona, summarizing their stance or a final reflection.
C.  Outro: Suggest a closing statement.

Guiding Principles for Outline Content:

Educational Priority: The primary goal is to make complex information accessible and understandable. Persona discussions and debates should illuminate the topic.
Authentic Persona Representation: When personas are used, their contributions should be consistent with their researched views and styles, as detailed in their persona research documents. They should be guided to select and emphasize information aligning with their persona.
Natural and Engaging Flow: Even with debates, the overall podcast should feel conversational and engaging.
Length Adherence: The proposed structure and depth of discussion in the outline should be feasible within the target podcast length (approx. 150 words per minute of dialogue). Allocate rough timings or emphasis to sections.
Objectivity in Narration: When a narrator/host is explaining core information from sources, it should be presented objectively before personas offer their specific takes.

Output Format:

VERY IMPORTANT: You MUST output your response as a single, valid JSON object. Do NOT use markdown formatting (e.g., ```json ... ```) around the JSON.
The JSON object must conform to the following Pydantic model structure:
{{
  "title_suggestion": "string (Suggested title for the podcast episode)",
  "summary_suggestion": "string (Suggested brief summary for the podcast episode)",
  "segments": [
    {{
      "segment_id": "string (Unique identifier, e.g., 'segment_1')",
      "segment_title": "string (Optional: The title or topic of this podcast segment)",
      "speaker_id": "string (Identifier for the speaker, e.g., 'Host', 'Persona_JohnDoe', 'Narrator')",
      "content_cue": "string (A brief cue or summary of the content to be covered in this segment)",
      "estimated_duration_seconds": "integer (Optional: Estimated duration for this segment in seconds)"
    }}
    // ... more segments
  ]
}}

Ensure all string fields are properly escaped within the JSON.
The 'segments' list should contain objects, each representing a distinct part of the podcast as outlined in the 'Outline Structure Requirements' section (Introduction, Main Body Segments, Conclusion).
For each segment in the 'segments' list:
- 'segment_id' should be unique for each segment (e.g., "intro_1", "body_1", "body_2", "conclusion_1").
- 'segment_title' should reflect the specific theme or topic of that segment.
- 'speaker_id' should indicate the primary speaker or interaction for that part of the segment (e.g., "Host", "Persona_A", "Persona_B_vs_Persona_A").
- 'content_cue' should be a concise instruction or summary for what needs to be said or discussed in that part of the segment. This is crucial for the dialogue generation step.
- 'estimated_duration_seconds' is optional but helpful for pacing.
"""
            logger.debug(f"PRD Outline Template Before Formatting:\n{prd_outline_prompt_template}")
            logger.debug(f"Outline Formatting Args - input_formatted_source_analyses_str (type {type(input_formatted_source_analyses_str)}): {input_formatted_source_analyses_str[:200]}...")
            logger.debug(f"Outline Formatting Args - input_formatted_persona_research_str (type {type(input_formatted_persona_research_str)}): {input_formatted_persona_research_str[:200]}...")
            logger.debug(f"Outline Formatting Args - input_desired_podcast_length_str (type {type(desired_podcast_length_str)}): {desired_podcast_length_str}")
            logger.debug(f"Outline Formatting Args - input_num_prominent_persons (type {type(num_prominent_persons)}): {num_prominent_persons}")
            logger.debug(f"Outline Formatting Args - input_formatted_names_prominent_persons_str (type {type(formatted_names_prominent_persons_str)}): {formatted_names_prominent_persons_str}")
            final_prompt = prd_outline_prompt_template.format(
                input_formatted_source_analyses_str=input_formatted_source_analyses_str,
                input_formatted_persona_research_str=input_formatted_persona_research_str,
                input_desired_podcast_length_str=desired_podcast_length_str,
                input_num_prominent_persons=num_prominent_persons,
                input_formatted_names_prominent_persons_str=formatted_names_prominent_persons_str
            )
            logger.debug(f"Final prompt for outline generation: {final_prompt[:500]}...")

            raw_response_text = await self.generate_text_async(final_prompt)
            
            # Attempt to strip markdown fences if present
            cleaned_response_text = raw_response_text.strip()
            if cleaned_response_text.startswith("```json") and cleaned_response_text.endswith("```"):
                cleaned_response_text = cleaned_response_text[7:-3].strip()
            elif cleaned_response_text.startswith("```") and cleaned_response_text.endswith("```"):
                cleaned_response_text = cleaned_response_text[3:-3].strip()

            try:
                # Parse the desired duration to seconds for time distribution validation
                total_duration_seconds = self._parse_duration_to_seconds(desired_podcast_length_str)
                logger.info(f"Parsed desired podcast length '{desired_podcast_length_str}' to {total_duration_seconds} seconds")
                
                # Clean keys before parsing, as Gemini sometimes adds extra spaces
                parsed_json_dict = json.loads(cleaned_response_text)
                parsed_json_dict = GeminiService._clean_keys_recursive(parsed_json_dict) 

                # Create the basic podcast outline from the LLM response
                podcast_outline = PodcastOutline(**parsed_json_dict)
                logger.info(f"Successfully generated podcast outline: {podcast_outline.title_suggestion}")
                
                # Validate and adjust segment durations and structure
                validated_podcast_outline = self._validate_and_adjust_segments(podcast_outline, total_duration_seconds)
                
                # Log the final segment structure
                segment_info = [f"{s.segment_id}: {s.estimated_duration_seconds}s" for s in validated_podcast_outline.segments]
                logger.info(f"Final podcast outline has {len(validated_podcast_outline.segments)} segments: {', '.join(segment_info)}")
                
                return validated_podcast_outline
            except json.JSONDecodeError as e:
                logger.error(f"LLM output for podcast outline was not valid JSON. Error: {e}. Raw response: '{cleaned_response_text[:500]}...'", exc_info=True)
                raise LLMProcessingError(f"LLM output for podcast outline was not valid JSON: {e}")
            except ValidationError as e:
                logger.error(f"LLM output for podcast outline did not match expected schema. Error: {e}. Raw response: '{cleaned_response_text[:500]}...'", exc_info=True)
                logger.debug(f"Problematic JSON string for outline: '{cleaned_response_text}'")
                raise LLMProcessingError(f"LLM output for podcast outline did not match expected schema: {e.errors()}")
            except Exception as e:
                logger.error(f"An unexpected error occurred during podcast outline generation. Error: {e}. Raw response: '{cleaned_response_text[:500]}...'", exc_info=True)
                raise LLMProcessingError(f"An unexpected error occurred during podcast outline generation: {e}")
    async def generate_dialogue_async(
        self,
        podcast_outline: PodcastOutline,
        source_analyses: list[SourceAnalysis],
        persona_research_docs: list[PersonaResearch],
        desired_podcast_length_str: str,
        num_prominent_persons: int,
        prominent_persons_details: list[tuple[str, str, str]], # (prominent_person_name, follower_name_initial, follower_system_assigned_gender)
        user_provided_custom_prompt: Optional[str] = None
    ) -> List[DialogueTurn]:
        """
        Generates dialogue for a podcast episode based on an outline, source analyses,
        persona research, and other parameters.
        
        This implementation iterates through each segment of the outline and generates
        dialogue turns specific to that segment's content, maintaining the proper flow
        and timing across segments.
        """
        logger.info(f"Generating dialogue for podcast outline '{podcast_outline.title_suggestion}' with {len(podcast_outline.segments)} segments")
        
        # Convert prominent persons details to a more usable format
        persona_mapping = {}
        gender_mapping = {}
        for name, follower_initial, gender in prominent_persons_details:
            persona_id = f"Persona_{follower_initial}"
            persona_mapping[persona_id] = name
            gender_mapping[persona_id] = gender
        
        # Add host gender mapping if not already included
        if "Host" not in gender_mapping:
            # Assign host a gender opposite to the first persona if any exist, otherwise default to "Male"
            host_gender = "Female" if gender_mapping and list(gender_mapping.values())[0] == "Male" else "Male"
            gender_mapping["Host"] = host_gender
        
        # Process each segment and generate dialogue turns
        all_dialogue_turns = []
        current_turn_id = 1
        
        # First, generate intro segment dialogue
        intro_segments = [s for s in podcast_outline.segments if s.segment_id.lower().startswith("intro")]
        main_segments = [s for s in podcast_outline.segments if not s.segment_id.lower().startswith("intro") and not s.segment_id.lower().startswith("conclu")]
        conclusion_segments = [s for s in podcast_outline.segments if s.segment_id.lower().startswith("conclu")]
        
        # Log segment structure
        logger.info(f"Segment structure: {len(intro_segments)} intro, {len(main_segments)} main, {len(conclusion_segments)} conclusion")
        
        # Process segments in proper order: intro → main → conclusion
        for segment_group in [intro_segments, main_segments, conclusion_segments]:
            for segment in segment_group:
                logger.info(f"Generating dialogue for segment '{segment.segment_id}': '{segment.segment_title}'")
                
                # Build segment-specific prompt
                segment_dialogue_prompt = self._build_segment_dialogue_prompt(
                    segment=segment,
                    podcast_outline=podcast_outline,
                    source_analyses=source_analyses,
                    persona_research_docs=persona_research_docs,
                    persona_mapping=persona_mapping,
                    user_provided_custom_prompt=user_provided_custom_prompt
                )
                
                # Generate dialogue for this segment
                segment_dialogue_turns = await self._generate_segment_dialogue(
                    segment=segment,
                    segment_dialogue_prompt=segment_dialogue_prompt,
                    current_turn_id=current_turn_id,
                    gender_mapping=gender_mapping
                )
                
                # Update current_turn_id for the next segment
                if segment_dialogue_turns:
                    current_turn_id = segment_dialogue_turns[-1].turn_id + 1
                    all_dialogue_turns.extend(segment_dialogue_turns)
                    logger.info(f"Generated {len(segment_dialogue_turns)} dialogue turns for segment '{segment.segment_id}'")
                else:
                    logger.warning(f"No dialogue turns generated for segment '{segment.segment_id}'. Using fallback approach.")
                    # Fallback: generate a simple host line for this segment
                    fallback_turn = DialogueTurn(
                        turn_id=current_turn_id,
                        speaker_id="Host",
                        speaker_gender=gender_mapping.get("Host", "Male"),
                        text=f"Let's talk about {segment.content_cue}",
                        source_mentions=[]
                    )
                    all_dialogue_turns.append(fallback_turn)
                    current_turn_id += 1
        
        # Validate and process the final dialogue turns
        if not all_dialogue_turns:
            logger.error("No dialogue turns were generated across all segments")
            raise LLMProcessingError("Failed to generate any dialogue turns for the podcast")
        
        logger.info(f"Successfully generated {len(all_dialogue_turns)} total dialogue turns across all segments")
        return all_dialogue_turns
    
    def _build_segment_dialogue_prompt(self, 
                                     segment: OutlineSegment,
                                     podcast_outline: PodcastOutline,
                                     source_analyses: list[SourceAnalysis],
                                     persona_research_docs: list[PersonaResearch],
                                     persona_mapping: dict,
                                     user_provided_custom_prompt: Optional[str] = None) -> str:
        """
        Build a prompt for generating dialogue specific to a segment of the podcast outline.
        """
        # Get basic podcast information for context
        podcast_title = podcast_outline.title_suggestion
        segment_context = f"Segment ID: {segment.segment_id}\nTitle: {segment.segment_title}\nSpeaker: {segment.speaker_id}\nContent: {segment.content_cue}\nDuration: {segment.estimated_duration_seconds} seconds"
        
        # Determine which persona research is relevant for this segment's speaker
        relevant_persona_research = None
        if segment.speaker_id.startswith("Persona_") and persona_mapping:
            persona_name = persona_mapping.get(segment.speaker_id)
            if persona_name:
                # Find matching persona research
                for pr in persona_research_docs:
                    if pr.persona_name.lower() == persona_name.lower():
                        relevant_persona_research = pr
                        break
        
        # Create the prompt template
        segment_prompt = f"""
LLM Prompt: Podcast Segment Dialogue Generation

Role: You are an expert podcast dialogue writer. Your task is to create natural, engaging dialogue for a specific segment of a podcast.

Podcast Information:
- Title: {podcast_title}
- Overall Theme: {podcast_outline.theme_description if hasattr(podcast_outline, 'theme_description') else 'Not specified'}

Current Segment Details:
{segment_context}

Instructions:
1. Write dialogue ONLY for this specific segment. The dialogue should directly address the content described in the segment's content cue.
2. The primary speaker for this segment should be {segment.speaker_id}.
3. Include appropriate responses or questions from other speakers as needed for natural conversation flow.
4. The dialogue should take approximately {segment.estimated_duration_seconds} seconds to speak aloud (roughly {segment.estimated_duration_seconds // 2} words).
5. Ensure the dialogue has a clear beginning and end appropriate for this segment's position in the overall podcast.
"""

        # Add persona-specific guidance if relevant
        if relevant_persona_research:
            segment_prompt += f"""

Persona Information for {segment.speaker_id}:
- Representing: {relevant_persona_research.persona_name}
- Key Viewpoints: {relevant_persona_research.key_viewpoints}
- Speaking Style: {relevant_persona_research.characteristic_speaking_style}

Important: Ensure the dialogue for {segment.speaker_id} authentically reflects the viewpoints and speaking style of {relevant_persona_research.persona_name}.
"""

        # Add source guidance
        if source_analyses:
            source_titles = [sa.source_title for sa in source_analyses if hasattr(sa, 'source_title') and sa.source_title]
            if source_titles:
                sources_str = "\n- ".join(source_titles)
                segment_prompt += f"""

Relevant Sources:
- {sources_str}

Reference these sources appropriately in the dialogue. Be factual and accurate to the source material.
"""

        # Add output format instructions
        segment_prompt += """

Output Format:
Provide the dialogue as a JSON array of dialogue turn objects. Each object should have:
- "turn_id": A sequential number starting from the provided current_turn_id
- "speaker_id": The ID of the speaker (e.g., "Host", "Persona_J", etc.)
- "text": The spoken dialogue text
- "source_mentions": An array of source reference strings (can be empty if no direct citations)

Example format:
[{"turn_id": 1, "speaker_id": "Host", "text": "Welcome to our discussion on...", "source_mentions": []},
 {"turn_id": 2, "speaker_id": "Persona_J", "text": "I believe that...", "source_mentions": ["Article: The Future of AI"]}]
"""

        # Add any user-provided custom instructions if present
        if user_provided_custom_prompt:
            segment_prompt += f"""

Additional User Instructions:
{user_provided_custom_prompt}
"""

        return segment_prompt

    async def _generate_segment_dialogue(self, 
                                      segment: OutlineSegment,
                                      segment_dialogue_prompt: str,
                                      current_turn_id: int,
                                      gender_mapping: dict) -> List[DialogueTurn]:
        """
        Generate dialogue turns for a specific segment using the LLM.
        """
        try:
            logger.debug(f"Sending segment dialogue prompt for segment {segment.segment_id}")
            raw_response_text = await self.generate_text_async(segment_dialogue_prompt)
            
            # Clean the response
            cleaned_response_text = raw_response_text.strip()
            if cleaned_response_text.startswith("```json") and cleaned_response_text.endswith("```"):
                cleaned_response_text = cleaned_response_text[7:-3].strip()
            elif cleaned_response_text.startswith("```") and cleaned_response_text.endswith("```"):
                cleaned_response_text = cleaned_response_text[3:-3].strip()
            
            # Parse the response
            parsed_json_list = json.loads(cleaned_response_text)
            parsed_json_list = GeminiService._clean_keys_recursive(parsed_json_list)
            
            # Validate it's a list
            if not isinstance(parsed_json_list, list):
                logger.error(f"LLM response for segment {segment.segment_id} dialogue was not a JSON list")
                return []
            
            # Create dialogue turns
            dialogue_turns: List[DialogueTurn] = []
            for i, item in enumerate(parsed_json_list):
                if not isinstance(item, dict):
                    logger.error(f"Item {i} in dialogue list for segment {segment.segment_id} is not a dict")
                    continue
                
                # Ensure the turn_id follows the sequence
                item['turn_id'] = current_turn_id + i
                
                # Add speaker gender if not present
                if 'speaker_gender' not in item and 'speaker_id' in item:
                    item['speaker_gender'] = gender_mapping.get(item['speaker_id'], 
                                                              "Male" if i % 2 == 0 else "Female")
                
                # Create the dialogue turn
                try:
                    dialogue_turns.append(DialogueTurn(**item))
                except ValidationError as e:
                    logger.error(f"Failed to create DialogueTurn for item {i} in segment {segment.segment_id}: {e}")
            
            return dialogue_turns
            
        except json.JSONDecodeError as e:
            logger.error(f"Failed to decode JSON for segment {segment.segment_id} dialogue: {e}")
            return []
        except Exception as e:
            logger.error(f"Error generating dialogue for segment {segment.segment_id}: {e}")
            return []

async def main_test():
    """
    Example usage function for testing the GeminiService directly.
    Ensure GOOGLE_API_KEY is set in your .env file or environment.
    """
    print("Testing GeminiService...")
    try:
        service = GeminiService()

        test_prompt_basic = "Write a very short, two-sentence story about a curious cat exploring a new garden."
        print(f"Sending basic prompt to Gemini: \"{test_prompt_basic}\"")
        generated_text = await service.generate_text_async(test_prompt_basic)
        print("\\nGenerated Text (Basic):")
        print(generated_text)

        print("\\nTesting source analysis...")
        sample_text_for_analysis = (
            "The recent advancements in renewable energy technology, particularly in solar panel efficiency "
            "and battery storage capacity, are poised to revolutionize the global energy market. "
            "Governments worldwide are increasingly implementing policies to support this transition, "
            "though challenges related to grid modernization and material sourcing remain significant."
        )
        analysis_result = await service.analyze_source_text_async(sample_text_for_analysis)
        print("Source Analysis Result:")
        print(analysis_result)

        print("\\nTesting persona research...")
        sample_person_name = "Dr. Evelyn Reed" # Add a sample person name
        persona_research_result = await service.research_persona_async(
            source_text=sample_text_for_analysis,
            person_name=sample_person_name # Pass the person_name
        )
        print("Persona Research Result:")
        print(persona_research_result)

        # --- Test data for podcast outline generation ---
        test_source_analyses = [analysis_result, "Second analysis: AI is rapidly changing industries."]
        test_persona_docs = [persona_research_result, "Second persona: A skeptical tech journalist."]
        test_desired_length = "5 minutes"
        
        print("\\nTesting podcast outline generation (PRD default prompt, 0 personas)...")
        outline_prd_0_personas = await service.generate_podcast_outline_async(
            source_analyses=test_source_analyses,
            persona_research_docs=[], # No specific personas for this test
            desired_podcast_length_str=test_desired_length,
            num_prominent_persons=0,
            names_prominent_persons_list=[]
        )
        print("Podcast Outline (PRD Default, 0 Personas):")
        print(outline_prd_0_personas)

        print("\\nTesting podcast outline generation (PRD default prompt, 2 personas)...")
        outline_prd_2_personas = await service.generate_podcast_outline_async(
            source_analyses=test_source_analyses,
            persona_research_docs=test_persona_docs,
            desired_podcast_length_str=test_desired_length,
            num_prominent_persons=2,
            names_prominent_persons_list=["Innovator Alpha", "Journalist Beta"]
        )
        print("Podcast Outline (PRD Default, 2 Personas):")
        print(outline_prd_2_personas)

        print("\\nTesting podcast outline generation (user-provided custom prompt)...")
        custom_user_prompt_for_outline = (
            "Based on the provided context, create a very brief, 2-point outline for a podcast "
            "discussing the future of renewable energy and AI. Keep it under 50 words."
            "Do not use the standard PRD outline structure. Just give me the 2 points."
        )
        # For a custom prompt, the PRD-specific inputs might not be directly used by the LLM
        # unless the custom prompt itself asks for them or has placeholders.
        # The service currently sends them if the PRD prompt is NOT used,
        # which might be redundant if the custom prompt doesn't use them.
        # For this test, we provide them anyway.
        outline_custom_user = await service.generate_podcast_outline_async(
            source_analyses=test_source_analyses,
            persona_research_docs=test_persona_docs,
            desired_podcast_length_str=test_desired_length, # May not be used by custom prompt
            num_prominent_persons=2, # May not be used by custom prompt
            names_prominent_persons_list=["Innovator Alpha", "Journalist Beta"], # May not be used
            user_provided_custom_prompt=custom_user_prompt_for_outline
        )
        print("Podcast Outline (User Custom Prompt):")
        print(outline_custom_user)

        # --- Test data for dialogue generation ---
        # Using outputs from previous outline tests as inputs here

        print("\nTesting dialogue generation (using 0-persona outline from PRD default)...")
        dialogue_0_personas = await service.generate_dialogue_async(
            podcast_outline=outline_prd_0_personas,
            source_analyses=test_source_analyses,
            persona_research_docs=[], # Matches the 0-persona outline scenario
            desired_podcast_length_str=test_desired_length,
            num_prominent_persons=0,
            prominent_persons_details=[]
        )
        print("Generated Dialogue (0 Personas):")
        print(dialogue_0_personas)

        print("\nTesting dialogue generation (using 2-persona outline from PRD default)...")
        # Define details for the prominent persons as per generate_dialogue_async signature
        # (prominent_person_name, follower_name_initial, follower_system_assigned_gender)
        test_prominent_persons_details_for_dialogue = [
            ("Innovator Alpha", "A", "Male"), # Example: Alpha, system assigns Male for TTS
            ("Journalist Beta", "B", "Female") # Example: Beta, system assigns Female for TTS
        ]
        dialogue_2_personas = await service.generate_dialogue_async(
            podcast_outline=outline_prd_2_personas,
            source_analyses=test_source_analyses,
            persona_research_docs=test_persona_docs, # These were used to generate the 2-persona outline
            desired_podcast_length_str=test_desired_length,
            num_prominent_persons=2,
            prominent_persons_details=test_prominent_persons_details_for_dialogue
        )
        print("Generated Dialogue (2 Personas):")
        print(dialogue_2_personas)

    except ValueError as ve:
        print(f"Configuration Error: {ve}")
    except Exception as e:
        print(f"An unexpected error occurred during testing: {e}")

if __name__ == "__main__":
    # This allows running this file directly for testing the GeminiService.
    # To run:
    # 1. Ensure you have GOOGLE_API_KEY set in your .env file in the project root.
    # 2. Navigate to the project root directory in your terminal.
    # 3. Run the script as a module: python -m app.llm_service
    asyncio.run(main_test())
