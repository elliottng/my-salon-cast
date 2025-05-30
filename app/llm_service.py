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
from pydantic import ValidationError
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
    async def generate_text_async(self, prompt: str, timeout_seconds: int = 180) -> str:
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

    def _clean_json_string_from_markdown(self, text: str) -> str:
        """
        Extracts a JSON string from a Markdown code block if present.
        Handles blocks like ```json ... ``` or ``` ... ```.
        """
        if not text:
            return ""
        # Regex to find content within ```json ... ``` or ``` ... ```
        # Making it non-greedy and handling potential leading/trailing whitespace within the block
        match = re.search(r"```(?:json)?\s*([\s\S]*?)\s*```", text, re.DOTALL)
        if match:
            return match.group(1).strip()
        return text.strip() # Fallback if no markdown block found, just strip whitespace

    async def analyze_source_text_async(self, source_text: str, analysis_instructions: str = None) -> SourceAnalysis:
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
                logger.info("Using default analysis prompt template, expecting JSON output for SourceAnalysis model")
            # Default analysis prompt, expecting JSON output
            prompt = (
                "Please analyze the following text and provide your analysis in JSON format. "
                "The JSON object should have exactly two keys: 'summary_points' and 'detailed_analysis'.\n"
                "- 'summary_points' should be a list of strings, where each string is a key summary point from the text.\n"
                "- 'detailed_analysis' should be a single string containing a more in-depth, free-form textual analysis of the source content.\n\n"
                "Example JSON format:\n"
                "{\n"
                "  \"summary_points\": [\"Key takeaway 1\", \"Important fact 2\", \"Main argument 3\"],\n"
                "  \"detailed_analysis\": \"The text discusses [topic] with a [tone/style]. It presents arguments such as [argument A] and [argument B], supported by [evidence]. The overall sentiment appears to be [sentiment]. Noteworthy stylistic features include [feature X]...\"\n"
                "}\n\n"
                f"Analyze this text:\n---\n{source_text}\n---"
            )
        
            logger.info(f"Constructed prompt of length {len(prompt)} characters")
            logger.info("Calling generate_text_async for source analysis...")
            
            try:
                response = await self.generate_text_async(prompt)
                logger.info(f"generate_text_async returned response of length: {len(response) if response else 0} characters")
                
                if not response:
                    logger.error("LLM returned empty response for source analysis")
                    raise LLMProcessingError("LLM returned empty response for source analysis")
                
                cleaned_response_str = self._clean_json_string_from_markdown(response)
                if not cleaned_response_str:
                    logger.error("LLM response was empty after cleaning Markdown.")
                    raise LLMProcessingError("LLM response was empty after cleaning Markdown.")

                try:
                    import json # Ensure json is imported in this scope if not already at top level
                    parsed_json = json.loads(cleaned_response_str)
                    logger.info("Successfully parsed JSON from cleaned LLM response.")
                except json.JSONDecodeError as e:
                    logger.error(f"Failed to parse JSON from cleaned LLM response: {e}", exc_info=True)
                    logger.error(f"Cleaned response snippet: {cleaned_response_str[:200]}")
                    raise LLMProcessingError(f"Response was not valid JSON after cleaning Markdown: {e}")

                try:
                    analysis_object = SourceAnalysis.model_validate(parsed_json)
                    logger.info("Successfully validated LLM response against SourceAnalysis model.")
                    logger.info("EXIT: analyze_source_text_async completed successfully")
                    return analysis_object
                except ValidationError as ve:
                    logger.error(f"Failed to validate LLM response against SourceAnalysis model: {ve}", exc_info=True)
                    logger.error(f"Parsed JSON data: {parsed_json}")
                    raise LLMProcessingError(f"Failed to validate the structure of the LLM response for source analysis: {ve}")
                
            except Exception as gen_error:
                logger.error(f"Error during generate_text_async call: {gen_error}", exc_info=True)
                logger.error(f"LLM API error during source analysis: {gen_error}")
                raise LLMProcessingError(f"LLM API error during source analysis: {gen_error}") from gen_error
                
        except ValueError as ve:
            logger.error(f"ValueError in analyze_source_text_async: {ve}")
            raise LLMProcessingError(f"Input validation error for source analysis: {ve}") from ve
            
        except Exception as e:
            logger.error(f"Unexpected error in analyze_source_text_async: {e}", exc_info=True)
            raise LLMProcessingError(f"Unexpected error during source analysis: {e}") from e
            
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
  "detailed_profile": "Provide a comprehensive textual profile of {person_name} based on the source text. This profile should synthesize their key viewpoints, opinions, or arguments. Also, describe their observed or inferred speaking style (e.g., 'analytical', 'passionate', 'cautious', 'storytelling'). Include any direct memorable quotes if they are prominent and illustrative of the persona. Combine all this information into a coherent narrative or summary string for this field."
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
            cleaned_response_text = self._clean_json_string_from_markdown(json_response_str)
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
        
        # For the simplified single segment approach, we just return the outline as-is
        # The original validation logic has been removed for clarity.
        # See comments below for reference on what was previously done.
        return podcast_outline
        
    # The following method contains commented out code that was part of the original
    # validation logic. Retained for reference or future reuse if needed.
    def _original_validate_and_adjust_segments_logic(self):
        """
        Original validation logic notes (retained for backward compatibility or future use):    
        If no duration provided for all segments, allocate based on ideal proportions:    
            - Intro: ~10-15% 
            - Body: ~70-80%
            - Conclusion: ~10-15%
        """
        # This method is not called anywhere - it's just a placeholder for the old code
        pass
        
        # Categorize segments example from old logic:
        # for segment in segments:
            # Example of old code:
            # if "intro" in segment.segment_id.lower() or "introduction" in segment.segment_title.lower():
            #     intro_segments.append(segment)
            # elif "conclu" in segment.segment_id.lower() or "conclusion" in segment.segment_title.lower() \
            #     or "outro" in segment.segment_id.lower() or "summary" in segment.segment_title.lower():
            #     conclusion_segments.append(segment)
            # else:
            #     body_segments.append(segment)
            # 
            # # If categorization failed, make a best guess based on position
            # if not intro_segments and not conclusion_segments and len(segments) >= 3:
            #     intro_segments = [segments[0]]
            #     conclusion_segments = [segments[-1]]
            #     body_segments = segments[1:-1]
            # elif not intro_segments and not conclusion_segments and len(segments) == 2:
            #     intro_segments = [segments[0]]
            #     conclusion_segments = [segments[1]]
            #     body_segments = []
            # elif not body_segments:
            # # Create at least one body segment if none exist
            # body_segments = [OutlineSegment(
            #     segment_id="body_1",
            #     segment_title="Main Discussion",
            #     speaker_id="Host",
            #     content_cue="Discuss the main points from the source material.",
            #     estimated_duration_seconds=0
            # )]
            #
            # # Calculate ideal durations based on proportions
            # intro_duration = int(total_duration_seconds * 0.15)  # 15%
            # conclusion_duration = int(total_duration_seconds * 0.15)  # 15%
            # body_duration = total_duration_seconds - intro_duration - conclusion_duration  # 70%
            # 
            # # Distribute durations within each category
            # if intro_segments:
            #     per_intro_segment = intro_duration // len(intro_segments)
            #     for segment in intro_segments:
            #         segment.estimated_duration_seconds = per_intro_segment
            # 
            # if body_segments:
            #     per_body_segment = body_duration // len(body_segments)
            #     for segment in body_segments:
            #         segment.estimated_duration_seconds = per_body_segment
            # 
            # if conclusion_segments:
            #     per_conclusion_segment = conclusion_duration // len(conclusion_segments)
            #     for segment in conclusion_segments:
            #         segment.estimated_duration_seconds = per_conclusion_segment
            # 
            # # Recombine segments in proper order
            # all_segments = intro_segments + body_segments + conclusion_segments
        
            # # Create updated outline with the same title/summary but adjusted segments
            # return PodcastOutline(
            #     title_suggestion=segments[0].segment_title if segments else "Generated Podcast",
            #     summary_suggestion="A podcast discussing the provided content.",
            #     segments=all_segments
            # )
    
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
        persona_details_map: dict[str, dict[str, str]],
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

            # Extract Persona IDs for the prompt
            available_persona_ids_list = []
            if persona_research_docs:
                for doc_json_str in persona_research_docs:
                    try:
                        doc_data = json.loads(doc_json_str) # Assuming each doc is a JSON string of PersonaResearch
                        if 'person_id' in doc_data:
                            available_persona_ids_list.append(doc_data['person_id'])
                    except json.JSONDecodeError:
                        logger.warning(f"Could not parse PersonaResearch JSON string: {doc_json_str[:100]}...")
            formatted_available_persona_ids_str = ", ".join(available_persona_ids_list) if available_persona_ids_list else "None available"

            # Calculate total seconds from desired podcast length string
            calculated_total_seconds = self._parse_duration_to_seconds(desired_podcast_length_str)
            # Calculate target word count based on 150 words per minute
            calculated_total_words = int(calculated_total_seconds / 60 * 150)

            # Format Persona Details Map for the prompt
            formatted_persona_details_str_parts = ["Persona Details (Mappings: Persona ID -> Invented Name, Real Name, Gender):"]
            if persona_details_map:
                for p_id, details in persona_details_map.items():
                    if p_id == "Host": # Skip host for this specific list, it's handled as a generic speaker
                        continue
                    formatted_persona_details_str_parts.append(
                        f"- Persona ID: '{p_id}' represents '{details.get('real_name', 'N/A')}' (Invented Name: '{details.get('invented_name', 'N/A')}', Gender: '{details.get('gender', 'N/A')}')"
                    )
            if len(formatted_persona_details_str_parts) == 1: # Only title was added
                formatted_persona_details_str_parts.append("No specific persona details provided beyond Host.")
            input_formatted_persona_details_str = "\n".join(formatted_persona_details_str_parts)

            # Format Names of Prominent Persons for PRD prompt
            formatted_names_prominent_persons_str: str
            if names_prominent_persons_list:
                formatted_names_prominent_persons_str = ", ".join(names_prominent_persons_list)
            else:
                formatted_names_prominent_persons_str = "None"

            # PRD 4.2.4 Prompt Template, MODIFIED for Multi-Segment Outline
            prd_outline_prompt_template = """LLM Prompt: Multi-Segment Podcast Outline Generation
Role: You are an expert podcast script developer and debate moderator. Your primary objective is to create a comprehensive, engaging, and informative multi-segment podcast outline based on the provided materials.

Overall Podcast Goals:

Educate: Clearly summarize and explain the key topics, findings, and information presented in the source documents for an audience of intellectually curious professionals.
Explore Perspectives: If prominent persons are specified, the podcast must clearly and forcefully articulate their known viewpoints and perspectives on the topics, drawing from their provided persona research documents. Each persona should have opportunities to speak.
Facilitate Viewpoint Diversity and Insightful Discussion/Debate: If these prominent persons have differing opinions, or if source materials present conflicting yet important viewpoints, the podcast should feature a healthy, robust debate and discussion, allowing for strong expression of these differing standpoints across various segments.  If the personas have differing points of view, please find opportunities for a persona to directly respond to the other persona with counterarguments

Inputs Provided to You:

Source Analysis Documents:
{input_formatted_source_analyses_str}

Persona Research Documents:
{input_formatted_persona_research_str}

Desired Podcast Length: {input_desired_podcast_length_str}
Total Podcast Duration (seconds): {calculated_total_seconds}
Target Total Word Count: {calculated_total_words} words (based on 150 words per minute)
Number of Prominent Persons Specified: {input_num_prominent_persons}
Names of Prominent People Specified: {input_formatted_names_prominent_persons_str}
Available Persona IDs (from Persona Research Documents, if any): {input_formatted_available_persona_ids_str}
Generic Speaker IDs available: "Host" (Invented Name: "Host", Gender: [Host's gender from persona_details_map]), "Narrator" (Typically neutral or assigned as needed)

Persona Details:
{input_formatted_persona_details_str}

Task: Generate a Multi-Segment Podcast Outline

Create a detailed, multi-segment outline for the entire podcast. This outline will serve as the blueprint for the subsequent dialogue writing step. The podcast should be divided into logical segments, each with a clear purpose and speaker focus.

Outline Structure Guidelines:

Your outline must break the podcast into several distinct segments. Each segment should contribute to the overall flow and goals. Consider segments for:
- Introduction/Opening Hook
- Topic Overview & Speaker Introductions: The 'Host' must introduce any personas speaking in a segment using their 'Invented Name' and clarifying which 'Real Name' they represent. For example: 'Host: Now, let's hear from Jarvis, an expert representing John Doe on this topic.' This should happen when a persona is first introduced or takes a significant speaking turn in a new context.
- Deep Dive into Theme 1 (Potentially featuring specific personas)
- Deep Dive into Theme 2 (Potentially featuring other personas or a debate)
- Points of Agreement/Conflict
- Conclusion/Summary

For each segment, you must specify:
- A unique `segment_id` (e.g., "seg_01_intro", "seg_02_theme1_johndoe").
- A concise `segment_title`.
- A `speaker_id` indicating the primary speaker or focus for that segment. This MUST be one of the Available Persona IDs (e.g., "persona_john_doe") or one of the Generic Speaker IDs ("Host", "Narrator").
- A detailed `content_cue` describing the topics, key points, questions, and discussion flow for that segment.
- A `target_word_count` for the segment's dialogue. This is the number of words you expect will be in the dialogue for this segment.
- An `estimated_duration_seconds` for the segment, calculated as (target_word_count / 150 * 60). This means each word takes 0.4 seconds (60 / 150) on average.

Guiding Principles for Outline Content:

Educational Priority: The primary goal is to make complex information accessible and understandable. Persona discussions and debates should illuminate the topic.
Authentic Persona Representation: When a persona's `speaker_id` is used, their contributions (guided by the `content_cue`) should align with their researched views.
Natural and Engaging Flow: The podcast should feel conversational and engaging throughout.
Length Adherence: The sum of all segment 'target_word_count' values MUST EXACTLY EQUAL {calculated_total_words} words. This is a non-negotiable constraint. Distribute content appropriately across segments to meet this total word count.
Detailed Content Cues: Each segment's content_cue MUST be comprehensive (at least 100-150 words) and specific, including: 
   - Key talking points in detail
   - Questions to be addressed
   - Specific facts or insights to include
   - Dialog flow and transitions
   - References to source material where relevant
   The content_cue serves as a detailed blueprint for the segment and should be thorough enough that another writer could create the same segment based solely on your cue.

Output Format:

⚠️ CRITICALLY IMPORTANT ⚠️
You MUST include BOTH the "target_word_count" AND "estimated_duration_seconds" fields for EACH segment. This is a non-negotiable requirement.

VERY IMPORTANT: You MUST output your response as a single, valid JSON object. Do NOT use markdown formatting around the JSON.
The JSON object must conform to the following structure:
{{
  "title_suggestion": "string (Suggested title for the podcast episode)",
  "summary_suggestion": "string (Suggested brief summary for the podcast episode)",
  "segments": [ // THIS MUST BE A LIST OF SEGMENT OBJECTS
    {{
      "segment_id": "string (Unique ID for this segment, e.g., seg_01_intro)",
      "segment_title": "string (Title for this segment, e.g., Introduction to Topic X)",
      "speaker_id": "string (Identifier for the primary speaker/focus, e.g., 'Host', 'persona_john_doe')",
      "content_cue": "string (MUST be comprehensive (100-150+ words) with detailed talking points, questions, specific facts, dialog flow, and source references)",
      "target_word_count": integer (Target number of words for this segment's dialogue),
      "estimated_duration_seconds": integer (Calculated as target_word_count / 150 * 60)
    }},
    {{
      "segment_id": "string (e.g., seg_02_deepdive)",
      "segment_title": "string (e.g., Exploring Viewpoint A)",
      "speaker_id": "string (e.g., 'persona_jane_smith')",
      "content_cue": "string (MUST be comprehensive (100-150+ words) with detailed talking points, questions, specific facts, dialog flow, and source references)",
      "target_word_count": integer (Target number of words for this segment),
      "estimated_duration_seconds": integer (Calculated from target_word_count)
    }}
    // ... more segments as needed ...
  ]
}}

Ensure all string fields are properly escaped within the JSON. The 'segments' array should contain multiple segment objects, each detailing a part of the podcast.
The `speaker_id` in each segment MUST be chosen from the persona IDs provided in the 'Persona Research Documents' (use their 'person_id' field) or be 'Host' or 'Narrator'.
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
                input_formatted_names_prominent_persons_str=formatted_names_prominent_persons_str,
                input_formatted_available_persona_ids_str=formatted_available_persona_ids_str,
                input_formatted_persona_details_str=input_formatted_persona_details_str,
                calculated_total_seconds=calculated_total_seconds,
                calculated_total_words=calculated_total_words
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
                raise LLMProcessingError(f"LLM output for podcast outline did not match expected schema: {e}")
            except Exception as e:
                logger.error(f"An unexpected error occurred during podcast outline generation. Error: {e}. Raw response: '{cleaned_response_text[:500]}...'", exc_info=True)
                raise LLMProcessingError(f"An unexpected error occurred during podcast outline generation: {e}")
    async def generate_dialogue_async(
        self,
        podcast_outline: PodcastOutline,
        source_analyses: list[SourceAnalysis],
        persona_research_docs: list[PersonaResearch],
        persona_details_map: dict[str, dict[str, str]], # (person_id -> {invented_name, gender, real_name})
        user_custom_prompt_for_dialogue: str = None
    ) -> List[DialogueTurn]:
        """
        Generates dialogue for a podcast episode based on an outline, source analyses,
        persona research, and other parameters.
        
        This implementation iterates through each segment of the outline and generates
        dialogue turns specific to that segment's content, maintaining the proper flow
        and timing across segments.
        """
        logger.info(f"Generating dialogue for podcast outline '{podcast_outline.title_suggestion}' with {len(podcast_outline.segments)} segments")
        
        # persona_details_map now directly provides person_id -> {invented_name, gender, real_name}
        # The speaker_id in OutlineSegment IS the person_id from PersonaResearch.
        # Generic speakers like "Host", "Narrator" are also expected to be in persona_details_map or handled as fixed entities.

        # Construct a string listing available persona speakers for the prompt, using their invented names.
        available_persona_speakers_list = []
        for p_id, details in persona_details_map.items():
            if p_id.lower() not in ["host", "narrator"]: # Exclude generic roles from this specific list if they are not personas
                invented_name = details.get("invented_name", p_id)
                real_name = details.get("real_name", "Unknown")
                available_persona_speakers_list.append(f"{invented_name} (representing {real_name}, ID: {p_id})")
        
        available_persona_speakers_str = ", ".join(available_persona_speakers_list) if available_persona_speakers_list else "No specific personas assigned invented names for dialogue."
        logger.info(f"Available persona speakers for dialogue prompt: {available_persona_speakers_str}")
        logger.info(f"Full persona_details_map for dialogue: {persona_details_map}")

        # Process each segment and generate dialogue turns
        all_dialogue_turns = []
        current_turn_id = 1
        
        # Simplified: Process all segments directly (expecting just one in V1)
        logger.info(f"Processing {len(podcast_outline.segments)} segments for dialogue generation")
        
        # Directly process segments without categorization
        for segment in podcast_outline.segments:
                logger.info(f"Generating dialogue for segment '{segment.segment_id}': '{segment.segment_title}'")
                
                # Build segment-specific prompt
                segment_dialogue_prompt = self._build_segment_dialogue_prompt(
                    segment=segment,
                    podcast_outline=podcast_outline,
                    source_analyses=source_analyses,
                    persona_research_docs=persona_research_docs,
                    persona_details_map=persona_details_map,
                    user_provided_custom_prompt=user_custom_prompt_for_dialogue
                )
                
                # Generate dialogue for this segment
                segment_dialogue_turns = await self._generate_segment_dialogue(
                    segment=segment,
                    segment_dialogue_prompt=segment_dialogue_prompt,
                    current_turn_id=current_turn_id,
                    persona_details_map=persona_details_map
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
                        speaker_gender=persona_details_map.get("Host", {}).get("gender", "male"),
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
                                     persona_details_map: dict[str, dict[str, str]],
                                     user_provided_custom_prompt: Optional[str] = None) -> str:
        """
        Build a prompt for generating dialogue specific to a segment of the podcast outline.
        """
        # Get basic podcast information for context
        podcast_title = podcast_outline.title_suggestion
        speaker_id_from_segment = segment.speaker_id
        speaker_details = persona_details_map.get(speaker_id_from_segment, {})
        invented_name = speaker_details.get("invented_name", speaker_id_from_segment)
        real_name_of_speaker = speaker_details.get("real_name", "Unknown")

        segment_context = f"Segment ID: {segment.segment_id}\nTitle: {segment.segment_title}\nSpeaker (Invented Name): {invented_name} (ID: {speaker_id_from_segment}, representing views of: {real_name_of_speaker})\nContent: {segment.content_cue}\nDuration: {segment.estimated_duration_seconds} seconds"
        
        # Determine which persona research is relevant for this segment's speaker
        relevant_persona_research = None
        if speaker_id_from_segment in persona_details_map and speaker_id_from_segment.lower() not in ["host", "narrator"]:
            for pr_json_str in persona_research_docs: # persona_research_docs is a list of JSON strings
                try:
                    pr_data = json.loads(pr_json_str)
                    if pr_data.get('person_id') == speaker_id_from_segment:
                        # Create a PersonaResearch object from the JSON data for use in the prompt
                        relevant_persona_research = PersonaResearch(**pr_data)
                        break
                except json.JSONDecodeError:
                    logger.warning(f"Could not parse PersonaResearch JSON string in _build_segment_dialogue_prompt: {pr_json_str[:100]}...")
                except Exception as e:
                    logger.warning(f"Error processing persona research JSON: {e}")
                    continue

        # Build available speakers string for the prompt
        available_speakers_parts = ["Available Speakers in this Podcast (Invented Name - Representing Real Name - Speaker ID):"]
        for p_id, details in persona_details_map.items():
            p_invented = details.get('invented_name', p_id)
            p_real = details.get('real_name', 'N/A')
            available_speakers_parts.append(f"- {p_invented} (representing {p_real}, ID: {p_id})")
        if "Narrator" not in persona_details_map and "narrator" not in persona_details_map: # Add Narrator if not explicitly mapped
                available_speakers_parts.append(f"- Narrator (ID: Narrator)")
        available_speakers_prompt_str = "\n".join(available_speakers_parts)
        
        # Create the prompt template
        segment_prompt = f"""
LLM Prompt: Podcast Segment Dialogue Generation

Role: You are an expert podcast dialogue writer. Your task is to create natural, engaging dialogue for a specific segment of a podcast.

Podcast Information:
- Title: {podcast_title}
- Overall Theme: {podcast_outline.theme_description if hasattr(podcast_outline, 'theme_description') else 'Not specified'}

Current Segment Details:
{segment_context}

{available_speakers_prompt_str}

Instructions:
1. Write dialogue ONLY for this specific segment. The dialogue should directly address the content described in the segment's content cue.
2. The primary speaker for this segment should be {invented_name} (who is speaker ID: {speaker_id_from_segment}, representing the views of {real_name_of_speaker}). Ensure their dialogue reflects their role.
3. Include appropriate responses or questions from other speakers as needed for natural conversation flow.
4. The dialogue should take approximately {segment.estimated_duration_seconds} seconds to speak aloud (roughly {segment.estimated_duration_seconds // 2} words).
5. Ensure the dialogue has a clear beginning and end appropriate for this segment's position in the overall podcast.
"""

        # Add persona-specific guidance if relevant
        if relevant_persona_research:
            segment_prompt += f"""

Persona Information for {invented_name} (Speaker ID: {speaker_id_from_segment}):
- Representing Views Of: {relevant_persona_research.name}
- Detailed Profile: {relevant_persona_research.detailed_profile}

Important: Ensure the dialogue for {invented_name} (Speaker ID: {speaker_id_from_segment}) authentically reflects the viewpoints and speaking style described in the detailed profile.
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
- "speaker_id": The ID of the speaker (e.g., "Host", "john-doe", "narrator"). This MUST be the actual person_id or generic role ID.
- "text": The spoken dialogue text
- "source_mentions": An array of source reference strings (can be empty if no direct citations)

Example format:
[{"turn_id": 1, "speaker_id": "Host", "text": "Welcome to our discussion on...", "source_mentions": []},
 {"turn_id": 2, "speaker_id": "john-doe", "text": "I believe that...", "source_mentions": ["Article: The Future of AI"]}]
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
                                      persona_details_map: dict[str, dict[str, str]]) -> List[DialogueTurn]:
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
                    speaker_id_from_llm = item['speaker_id']
                    # Look up in persona_details_map
                    speaker_info = persona_details_map.get(speaker_id_from_llm)
                    if speaker_info and 'gender' in speaker_info:
                        item['speaker_gender'] = speaker_info['gender']
                    else:
                        # Fallback if speaker_id not in map or gender not specified
                        # For "Host" or "Narrator", if not in map, assign a default
                        if speaker_id_from_llm.lower() == "host":
                            item['speaker_gender'] = "Male"  # Default Host gender
                        elif speaker_id_from_llm.lower() == "narrator":
                            item['speaker_gender'] = "Neutral"  # Default Narrator gender
                        else:
                            # Fallback for any other unexpected speaker_id
                            logger.warning(f"Speaker ID '{speaker_id_from_llm}' not found in persona_details_map or gender missing. Defaulting to 'neutral'.")
                            item['speaker_gender'] = "neutral"
                
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
