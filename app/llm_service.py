# app/llm_service.py

import google.generativeai as genai
import os
import sys
import time
import re
import json
import random
from datetime import datetime
from typing import List, Dict, Optional, Union, Any
import logging
import functools
import asyncio
from concurrent.futures import ThreadPoolExecutor, Future
import atexit

from dotenv import load_dotenv
from pydantic import ValidationError
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type
from pydantic_ai import Agent
from pydantic_ai.models.gemini import GeminiModel
import logfire
from app.config import get_config
from app.prompts import (
    SOURCE_ANALYSIS_TEMPLATE,
    PERSONA_RESEARCH_TEMPLATE,
    PODCAST_OUTLINE_TEMPLATE,
    SEGMENT_DIALOGUE_TEMPLATE,
)

from google.api_core.exceptions import (
    DeadlineExceeded,
    ServiceUnavailable,
    ResourceExhausted,
    InternalServerError
)
from google.ai.generativelanguage_v1beta.types import GenerationConfig
from pydantic import ValidationError

from app.podcast_models import PersonaResearch, PodcastOutline, DialogueTurn, SourceAnalysis, OutlineSegment
from app.common_exceptions import LLMProcessingError

# Lists for persona invented names by gender
male_names = [
    "Alexander", "Benjamin", "Christopher", "Daniel", "Ethan", "Frederick", "George", 
    "Henry", "Isaac", "James", "Kenneth", "Liam", "Michael", "Nathan", "Oliver", 
    "Paul", "Quentin", "Robert", "Samuel", "Thomas", "William"
]

female_names = [
    "Amelia", "Beatrice", "Catherine", "Diana", "Elizabeth", "Fiona", "Grace", 
    "Hannah", "Isabella", "Julia", "Katherine", "Lily", "Margaret", "Natalie", 
    "Olivia", "Patricia", "Rachel", "Sophia", "Taylor", "Victoria", "Zoe"
]

neutral_names = [
    "Alex", "Bailey", "Cameron", "Dakota", "Eden", "Finley", "Jordan", "Morgan", 
    "Parker", "Quinn", "Riley", "Sam", "Taylor", "Avery", "Casey", "Drew", 
    "Emerson", "Jamie", "Kai", "Reese"
]

# Names for personae are defined here, but voice profiles are now fetched from the TTS service
# to ensure we always have valid voice IDs

# Configure logger
logger = logging.getLogger(__name__)
# Basic configuration, can be adjusted based on project-wide logging setup
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')

class LLMNotInitializedError(ValueError):
    """Custom exception for LLM service initialization errors."""
    pass

class GeminiService:
    # Shared thread pool executor for LLM operations (similar to TTS service pattern)
    _llm_executor = None
    
    @classmethod
    def _get_llm_executor(cls):
        """Get or create the shared LLM thread pool executor."""
        if cls._llm_executor is None or cls._llm_executor._shutdown:
            cls._llm_executor = ThreadPoolExecutor(
                max_workers=20, 
                thread_name_prefix="llm_worker"
            )
            # Register shutdown handler
            atexit.register(cls._llm_executor.shutdown)
            logger.info("Created shared LLM thread pool executor with 20 workers")
        return cls._llm_executor

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

    def __init__(self, api_key: Optional[str] = None, tts_service=None):
        """
        Initializes the Gemini Service.
        API key is read from GEMINI_API_KEY environment variable if not provided.
        """
        load_dotenv() # Load environment variables from env file
        
        if api_key is None:
            api_key = os.getenv("GEMINI_API_KEY")
            
        if not api_key:
            raise LLMNotInitializedError("API key for Gemini service is required. Set GEMINI_API_KEY environment variable or pass it directly.")
        
        genai.configure(api_key=api_key)
        # Using gemini-2.0-flash-exp as per upgrade to Gemini 2.0 Flash.
        # Consider making the model name configurable if needed in the future.
        self.model = genai.GenerativeModel('gemini-2.0-flash-exp')
        
        # Store TTS service for voice profile lookup
        self.tts_service = tts_service
        
        # Initialize Pydantic AI agent (always enabled after Phase 1 refactoring)
        logger.info("Initializing Pydantic AI agent for Gemini service")
        # Create Pydantic AI model with standard approach
        pydantic_model = GeminiModel('gemini-2.0-flash-exp')
        # Create a generic agent that can handle both string and structured outputs
        self.pydantic_agent = Agent(
            model=pydantic_model,
            system_prompt=""  # Empty system prompt for default behavior
        )
        # Configure Logfire if credentials are available (either in project dir or env)
        logfire_configured = (
            os.path.exists('.logfire/logfire_credentials.json') or 
            os.environ.get('LOGFIRE_TOKEN') is not None
        )
        
        if logfire_configured:
            try:
                logfire.configure()
                # Instrument all Pydantic AI agents globally
                logfire.instrument_pydantic_ai()
                logger.info("Logfire observability configured successfully")
            except Exception as e:
                logger.warning(f"Failed to configure Logfire: {e}")
        else:
            logger.info("Logfire credentials not found, skipping observability setup")
        logger.info("Pydantic AI agent initialized successfully")

    async def generate_text_async(self, prompt: str, timeout_seconds: int = 180, result_type: Optional[type] = None) -> Union[str, Any]:
        """
        Asynchronously generates text based on the given prompt using the configured Gemini model.
        Uses Pydantic AI with support for structured output via result_type parameter.
        
        Args:
            prompt: The prompt to send to the model
            timeout_seconds: Maximum time to wait for the API call in seconds (default: 180)
            result_type: Optional type for structured output
            
        Returns:
            The generated text response (string) or structured output if result_type is provided
            
        Raises:
            TimeoutError: If the API call exceeds the timeout_seconds
            ValueError: If the prompt is empty
            ValidationError: If structured output validation fails
            RuntimeError: For other unexpected errors
        """
        logger.info("ENTRY: generate_text_async method called")
        logger.info(f"Prompt length: {len(prompt) if prompt else 0} characters with {timeout_seconds}s timeout")
        logger.info(f"Result type: {result_type}")
        
        if not prompt:
            logger.error("Prompt cannot be empty.")
            raise ValueError("Prompt cannot be empty.")
        
        try:
            # Configure timeout and retries
            import pydantic_ai
            from pydantic_ai.exceptions import UserError, ModelRetry
            
            # Set up run context with timeout and retries
            run_kwargs = {
                'message_history': [],
                'model_settings': {
                    'timeout': timeout_seconds,
                }
            }
            
            # Check if Logfire is configured
            logfire_configured = (
                os.path.exists('.logfire/logfire_credentials.json') or 
                os.environ.get('LOGFIRE_TOKEN') is not None
            )
            
            if result_type:
                logger.info(f"Running Pydantic AI agent for structured output type: {result_type}")
                # Create a specialized agent for this result type
                agent = Agent(
                    model=self.pydantic_agent.model,
                    result_type=result_type,
                    system_prompt=""
                )
                
                # Logfire is instrumented globally, just run the agent
                result = await agent.run(prompt, **run_kwargs)
                logger.info(f"Pydantic AI call completed successfully, result type: {type(result.data)}")
                logger.info("EXIT: generate_text_async completed successfully with structured output")
                return result.data
            else:
                logger.info("Running Pydantic AI agent for string output")
                
                # Logfire is instrumented globally, just run the agent
                result = await self.pydantic_agent.run(prompt, **run_kwargs)
                logger.info(f"Pydantic AI call completed successfully, response length: {len(result.data) if result.data else 0}")
                logger.info("EXIT: generate_text_async completed successfully with string output")
                return result.data
                    
        except asyncio.TimeoutError as e:
            logger.error(f"Pydantic AI call timed out after {timeout_seconds} seconds")
            logger.info("EXIT: generate_text_async with timeout")
            # For backward compatibility, return error JSON for timeout
            error_json = '{"error": "Gemini API timeout", "details": "API call timed out after ' + str(timeout_seconds) + ' seconds"}'
            logger.error(f"Returning error JSON: {error_json}")
            return error_json
            
        except ValidationError as e:
            logger.error(f"Pydantic validation error: {e}", exc_info=True)
            logger.info("EXIT: generate_text_async with validation error")
            # Re-raise ValidationError as it's already handled by callers
            raise
            
        except UserError as e:
            logger.error(f"Pydantic AI user error: {e}", exc_info=True)
            logger.info("EXIT: generate_text_async with user error")
            # Map to ValueError for backward compatibility
            raise ValueError(str(e)) from e
            
        except ModelRetry as e:
            logger.error(f"Pydantic AI model retry exhausted: {e}", exc_info=True)
            logger.info("EXIT: generate_text_async with retry exhausted")
            # Map to appropriate exception based on the underlying cause
            if "rate limit" in str(e).lower() or "quota" in str(e).lower():
                raise ResourceExhausted(str(e)) from e
            elif "timeout" in str(e).lower() or "deadline" in str(e).lower():
                raise DeadlineExceeded(str(e)) from e
            else:
                raise RuntimeError(f"Failed to generate text after retries: {e}") from e
            
        except Exception as e:
            # Map common Pydantic AI exceptions to existing exceptions
            error_message = str(e).lower()
            if "rate limit" in error_message or "quota" in error_message:
                logger.error(f"Rate limit/quota error: {e}", exc_info=True)
                raise ResourceExhausted(str(e)) from e
            elif "timeout" in error_message or "deadline" in error_message:
                logger.error(f"Timeout/deadline error: {e}", exc_info=True)
                raise DeadlineExceeded(str(e)) from e
            else:
                # General catch-all for any other errors
                logger.error(f"Unexpected error in generate_text_async: {e.__class__.__name__} - {e}", exc_info=True)
                logger.info("EXIT: generate_text_async with exception")
                raise RuntimeError(f"Failed to generate text due to an unexpected error: {e}") from e

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
                prompt = SOURCE_ANALYSIS_TEMPLATE.format(source_text=source_text)
            
            logger.info("Calling generate_text_async with text analysis prompt")
            
            # Use Pydantic AI for structured SourceAnalysis output
            logger.info("Using Pydantic AI for structured SourceAnalysis output")
            return await self.generate_text_async(prompt, timeout_seconds=180, result_type=SourceAnalysis)
            
        except ValueError as ve:
            logger.error(f"ValueError in analyze_source_text_async: {ve}")
            raise LLMProcessingError(f"Input validation error for source analysis: {ve}") from ve
            
        except Exception as e:
            logger.error(f"Unexpected error in analyze_source_text_async: {e}", exc_info=True)
            raise LLMProcessingError(f"Unexpected error during source analysis: {e}") from e
            
        finally:
            logger.info("EXIT: analyze_source_text_async method complete")

    def _clean_keys_recursive(self, obj):
        # logger.debug(f"_clean_keys_recursive processing type: {type(obj)}")
        if isinstance(obj, dict):
            new_dict = {}
            for key, value in obj.items():
                stripped_key = key.strip()
                # logger.debug(f"Original key: '{key}', Stripped key: '{stripped_key}'")
                new_dict[stripped_key] = self._clean_keys_recursive(value)
            return new_dict
        elif isinstance(obj, list):
            return [self._clean_keys_recursive(element) for element in obj]
        return obj

    def _clean_json_string_from_markdown(self, text: str) -> str:
        """
        Extracts a JSON string from a Markdown code block if present.
        Handles blocks like ```json ... ``` or ``` ... ```.
        Includes advanced recovery for malformed responses.
        """
        if not text:
            return ""
        
        cleaned_text = text.strip()
        
        # Regex to find content within ```json ... ``` or ``` ... ```
        # Making it non-greedy and handling potential leading/trailing whitespace within the block
        match = re.search(r"```(?:json)?\s*([\s\S]*?)\s*```", cleaned_text, re.DOTALL)
        if match:
            cleaned_text = match.group(1).strip()
            
        # Advanced recovery: Try to find a JSON object even in malformed responses
        try:
            # Look for the first { and last } to extract potential JSON
            start_idx = cleaned_text.find('{')
            end_idx = cleaned_text.rfind('}')
            if start_idx != -1 and end_idx != -1 and start_idx < end_idx:
                potential_json = cleaned_text[start_idx:end_idx+1]
                # Validate if this is parseable JSON
                json.loads(potential_json)
                # If we reach here, it's valid JSON
                logger.info(f"Successfully extracted valid JSON from potentially malformed response")
                return potential_json
        except json.JSONDecodeError:
            # If extraction attempt fails, fall back to original cleaned text
            logger.warning(f"JSON extraction recovery attempt failed, falling back to original cleaned text")
            pass
            
        return cleaned_text

    async def research_persona_async(self, source_text: str, person_name: str) -> PersonaResearch:
        """
        Conducts persona research based on the provided source text.
        Allows for specifying a focus for the persona research.
        Also determines gender, invented name, and TTS voice for the persona.
        """
        if not source_text:
            raise ValueError("Source text for persona research cannot be empty.")
        if not person_name:
            raise ValueError("Person name for persona research cannot be empty.")

        # Create a simple person_id from the name (e.g., for filenames or internal references)
        # This can be made more robust if needed (e.g., handling special characters, ensuring uniqueness)
        person_id = person_name.lower().replace(' ', '_').replace('.', '')

        # We'll use the global name and voice profile lists defined at the top of the file

        prompt = PERSONA_RESEARCH_TEMPLATE.format(
            person_name=person_name,
            person_id=person_id,
            person_name_upper=person_name.upper(),
            source_text=source_text
        )
        
        logger.info(f"Generating persona research for '{person_name}' with prompt (first 200 chars): {prompt[:200]}...")
        
        try:
            # Use Pydantic AI for structured PersonaResearch output
            logger.info(f"Using Pydantic AI for structured PersonaResearch output for '{person_name}'")
            persona_research = await self.generate_text_async(prompt, result_type=PersonaResearch, timeout_seconds=420)
            # Convert to dict for the existing post-processing logic
            parsed_json = persona_research.model_dump()
            logger.info(f"Successfully received structured PersonaResearch for '{person_name}'")
                
            # Process gender and assign appropriate invented name and TTS voice ID
            # First normalize to lowercase for validation
            raw_gender = parsed_json.get('gender', '').lower()
                
            # Then capitalize for TTS service compatibility
            if not raw_gender or raw_gender not in ['male', 'female', 'neutral']:
                logger.warning(f"Invalid or missing gender '{raw_gender}' for {person_name}, defaulting to 'Neutral'")
                gender = 'Neutral'
            elif raw_gender == 'male':
                gender = 'Male'
            elif raw_gender == 'female':
                gender = 'Female'
            else:  # neutral
                gender = 'Neutral'
                    
            logger.info(f"Normalized gender for {person_name}: '{raw_gender}' -> '{gender}'")
                
            # Respect LLM-generated invented_name, fallback if missing
            if 'invented_name' in parsed_json and parsed_json['invented_name'] and parsed_json['invented_name'].strip():
                invented_name = parsed_json['invented_name'].strip()
                logger.info(f"Using LLM-generated invented name for {person_name}: '{invented_name}'")
            else:
                # Fallback: assign name based on gender if LLM didn't provide one
                if gender == 'Male':
                    invented_name = random.choice(male_names)
                elif gender == 'Female':
                    invented_name = random.choice(female_names)
                else:  # Neutral
                    invented_name = random.choice(neutral_names)
                logger.info(f"LLM did not provide invented name for {person_name}, assigned fallback: '{invented_name}'")
                
            # Get voice profile from TTS service if available
            voice_profile = None
            if self.tts_service:
                # Get list of voices for this gender from the TTS service cache
                voices = self.tts_service.get_voices_by_gender(gender)
                if voices:
                    voice_profile = random.choice(voices)
                    tts_voice_id = voice_profile['voice_id']
                    logger.info(f"Using cached voice profile from TTS service for {gender} gender: {tts_voice_id}")
                else:
                    logger.warning(f"No voice profiles available for {gender} gender in TTS service cache")
                    # Create a fallback voice profile using Chirp3-HD backup voices
                    chirp3_backup_voices = {
                        'Male': ['en-US-Chirp3-HD-Achird', 'en-GB-Chirp3-HD-Algenib', 'en-AU-Chirp3-HD-Algieba'],
                        'Female': ['en-US-Chirp3-HD-Achernar', 'en-GB-Chirp3-HD-Aoede', 'en-AU-Chirp3-HD-Autonoe'],
                        'Neutral': ['en-US-Chirp3-HD-Achird', 'en-GB-Chirp3-HD-Achernar', 'en-AU-Chirp3-HD-Algenib']
                    }
                    backup_voice = random.choice(chirp3_backup_voices.get(gender, chirp3_backup_voices['Neutral']))
                    voice_profile = {
                        'voice_id': backup_voice,
                        'speaking_rate': random.uniform(0.85, 1.15)
                    }
                    tts_voice_id = backup_voice
                    logger.info(f"Using Chirp3-HD backup voice for {gender} gender: {tts_voice_id}")
            else:
                logger.warning("TTS service not available, using gender-based voice selection only")
                # Create a fallback voice profile using Chirp3-HD backup voices
                chirp3_backup_voices = {
                    'Male': ['en-US-Chirp3-HD-Achird', 'en-GB-Chirp3-HD-Algenib', 'en-AU-Chirp3-HD-Algieba'],
                    'Female': ['en-US-Chirp3-HD-Achernar', 'en-GB-Chirp3-HD-Aoede', 'en-AU-Chirp3-HD-Autonoe'],
                    'Neutral': ['en-US-Chirp3-HD-Achird', 'en-GB-Chirp3-HD-Achernar', 'en-AU-Chirp3-HD-Algenib']
                }
                backup_voice = random.choice(chirp3_backup_voices.get(gender, chirp3_backup_voices['Neutral']))
                voice_profile = {
                    'voice_id': backup_voice,
                    'speaking_rate': random.uniform(0.85, 1.15)
                }
                tts_voice_id = backup_voice
                logger.info(f"Using Chirp3-HD backup voice for {gender} gender: {tts_voice_id}")
                
            logger.info(f"Assigned {person_name}: gender={gender}, invented_name={invented_name}, voice={tts_voice_id if tts_voice_id else 'based on gender'}, speaking_rate={voice_profile['speaking_rate']}")

            # Store the full voice profile parameters for future use
            voice_params = {}
            # Copy all parameters from the voice profile
            if voice_profile:
                for key, value in voice_profile.items():
                    if key != 'language_codes':  # Skip language_codes, we don't need it in the params
                        voice_params[key] = value
                
            # Update the parsed JSON with the additional fields
            parsed_json['invented_name'] = invented_name
            parsed_json['gender'] = gender  # Ensure normalized lowercase gender
            parsed_json['tts_voice_id'] = tts_voice_id
            parsed_json['tts_voice_params'] = voice_params  # Store full voice parameters
            parsed_json['creation_date'] = datetime.now().isoformat()
            parsed_json['source_context'] = source_text[:500] + ('...' if len(source_text) > 500 else '')  # Add source context
                
            # Create the PersonaResearch object with all fields
            persona_research_data = PersonaResearch(**parsed_json)
            logger.info(f"Successfully created enhanced PersonaResearch for '{person_name}'")
            return persona_research_data
            
        except json.JSONDecodeError as e:
            logger.error(f"JSONDecodeError parsing persona research for '{person_name}': {e}. LLM Output: {parsed_json[:500] if 'parsed_json' in locals() else 'Not available'}...", exc_info=True)
            raise ValueError(f"Failed to parse LLM response as JSON for persona '{person_name}'.") from e
        except ValidationError as e: 
            logger.error(f"ValidationError validating persona research for '{person_name}': {e}. LLM Output: {parsed_json[:500] if 'parsed_json' in locals() else 'Not available'}...", exc_info=True)
            raise ValueError(f"LLM response for persona '{person_name}' did not match expected PersonaResearch structure.") from e
        except Exception as e: # Catches errors from generate_text_async, or other unexpected issues like TypeError if json_response_str was None and json.loads tried it.
            logger.error(f"Unexpected error during persona research for '{person_name}': {e.__class__.__name__} - {e}. LLM Output was: {parsed_json[:500] if 'parsed_json' in locals() else 'Not available'}...", exc_info=True)
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
            
        # 3. Ensure all segments have valid durations and word counts
        for segment in segments:
            if segment.estimated_duration_seconds is None or segment.estimated_duration_seconds <= 0:
                # Default to 30 seconds if missing or invalid
                logger.warning(f"Segment '{segment.segment_id}' had invalid duration. Setting default 30s.")
                segment.estimated_duration_seconds = 30
                
            if segment.target_word_count is None or segment.target_word_count <= 0:
                # Calculate word count based on duration (150 words per minute)
                logger.warning(f"Segment '{segment.segment_id}' had invalid word count. Calculating from duration.")
                segment.target_word_count = int(segment.estimated_duration_seconds / 60 * 150)
        
        # 4. Enforce the total duration by scaling segments proportionally
        current_total_duration = sum(segment.estimated_duration_seconds for segment in segments)
        logger.info(f"Podcast outline: LLM specified {current_total_duration}s duration, desired is {total_duration_seconds}s")
        
        # Only scale if significantly different (more than 10% difference)
        if abs(current_total_duration - total_duration_seconds) > (total_duration_seconds * 0.1):
            # Scale all segments proportionally
            scale_factor = total_duration_seconds / current_total_duration if current_total_duration > 0 else 1.0
            logger.info(f"Scaling podcast segment durations by factor of {scale_factor:.2f}")
            
            # Scale each segment's duration and target word count
            for segment in segments:
                original_duration = segment.estimated_duration_seconds
                segment.estimated_duration_seconds = max(15, int(original_duration * scale_factor))  # Minimum 15s segments
                # Update target word count based on the new duration
                segment.target_word_count = int(segment.estimated_duration_seconds / 60 * 150)
                logger.debug(f"Segment '{segment.segment_id}': {original_duration}s → {segment.estimated_duration_seconds}s, {segment.target_word_count} words")
        
        # Validate we've now hit the target duration
        new_total_duration = sum(segment.estimated_duration_seconds for segment in segments)
        logger.info(f"Adjusted podcast duration: {new_total_duration}s (target: {total_duration_seconds}s)")
        
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
        intro_duration = int(total_duration_seconds * 0.15)
        body_duration = int(total_duration_seconds * 0.7)
        conclusion_duration = total_duration_seconds - intro_duration - body_duration
        
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
                        # If it's already a PersonaResearch object
                        if isinstance(doc_json_str, PersonaResearch):
                            if doc_json_str.person_id:
                                available_persona_ids_list.append(doc_json_str.person_id)
                        # If it's a JSON string (backward compatibility)
                        elif isinstance(doc_json_str, str):
                            pr_data = json.loads(doc_json_str) # Assuming each doc is a JSON string of PersonaResearch
                            if 'person_id' in pr_data:
                                available_persona_ids_list.append(pr_data['person_id'])
                    except json.JSONDecodeError:
                        logger.warning(f"Could not parse PersonaResearch JSON string: {doc_json_str[:100]}...")
                    except Exception as e:
                        logger.warning(f"Error processing persona research: {e}")
                        continue

            # Calculate total seconds from desired podcast length string
            calculated_total_seconds = self._parse_duration_to_seconds(desired_podcast_length_str)
            # Calculate target word count based on 150 words per minute
            calculated_total_words = int(calculated_total_seconds / 60 * 150)
            
            # Pre-calculate word counts for each segment (redistributed percentages after removing overview)
            intro_words = int(calculated_total_words * 0.08)  # Increased from 5% to 8%
            theme1_words = int(calculated_total_words * 0.13)  # Increased from 10% to 13%
            theme2_words = int(calculated_total_words * 0.13)  # Increased from 10% to 13%
            discussion_words = int(calculated_total_words * 0.50)  # Stays 50%
            conclusion_words = int(calculated_total_words * 0.16)  # Increased from 15% to 16%
            
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
            prd_outline_prompt_template = PODCAST_OUTLINE_TEMPLATE
            logger.debug(f"PRD Outline Template Before Formatting:\n{prd_outline_prompt_template}")
            
            # Create a format dict with all the variables needed in the template
            format_dict = {
                "input_formatted_source_analyses_str": input_formatted_source_analyses_str,
                "input_formatted_persona_research_str": input_formatted_persona_research_str,
                "input_desired_podcast_length_str": desired_podcast_length_str,
                "input_num_prominent_persons": num_prominent_persons,
                "input_formatted_names_prominent_persons_str": formatted_names_prominent_persons_str,
                "input_formatted_available_persona_ids_str": ", ".join(available_persona_ids_list) if available_persona_ids_list else "None available",
                "input_formatted_persona_details_str": input_formatted_persona_details_str,
                "calculated_total_seconds": calculated_total_seconds,
                "calculated_total_words": calculated_total_words,
                "intro_words": intro_words,
                "theme1_words": theme1_words,
                "theme2_words": theme2_words,
                "discussion_words": discussion_words,
                "conclusion_words": conclusion_words
            }
            
            # Format the prompt template with all variables
            final_prompt = prd_outline_prompt_template.format(**format_dict)
            logger.debug(f"Final prompt for outline generation: {final_prompt[:500]}...")
            
            # Use extended timeout (360s) for podcast outline generation as it's a complex prompt
            raw_response_text = await self.generate_text_async(final_prompt, timeout_seconds=360)
            
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
                parsed_json_dict = self._clean_keys_recursive(parsed_json_dict) 

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
            # Handle both formats: PersonaResearch objects or JSON strings for backward compatibility
            for pr_item in persona_research_docs:
                try:
                    # If it's already a PersonaResearch object
                    if isinstance(pr_item, PersonaResearch):
                        if pr_item.person_id == speaker_id_from_segment:
                            relevant_persona_research = pr_item
                            break
                    # If it's a JSON string (backward compatibility)
                    elif isinstance(pr_item, str):
                        pr_data = json.loads(pr_item)
                        if 'person_id' in pr_data:
                            relevant_persona_research = PersonaResearch(**pr_data)
                            break
                except json.JSONDecodeError:
                    logger.warning(f"Could not parse PersonaResearch JSON string in _build_segment_dialogue_prompt: {pr_item[:100]}...")
                except Exception as e:
                    logger.warning(f"Error processing persona research: {e}")
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
        
        # Build persona guidance string
        persona_guidance = ""
        if relevant_persona_research:
            persona_guidance = f"""Persona Information for {invented_name} (Speaker ID: {speaker_id_from_segment}):
- Representing Views Of: {relevant_persona_research.name}
- Detailed Profile: {relevant_persona_research.detailed_profile}

Important: Ensure the dialogue for {invented_name} (Speaker ID: {speaker_id_from_segment}) authentically reflects the viewpoints and speaking style described in the detailed profile."""

        # Build source guidance string
        source_guidance = ""
        if source_analyses:
            source_titles = [sa.source_title for sa in source_analyses if hasattr(sa, 'source_title') and sa.source_title]
            if source_titles:
                sources_str = "\n- ".join(source_titles)
                source_guidance = f"""Relevant Sources:
- {sources_str}

Reference these sources appropriately in the dialogue. Be factual and accurate to the source material."""

        # Build user custom prompt string
        user_custom_prompt = ""
        if user_provided_custom_prompt:
            user_custom_prompt = f"""Additional User Instructions:
{user_provided_custom_prompt}"""

        # Calculate target word count
        target_word_count = segment.target_word_count if segment.target_word_count is not None else int(segment.estimated_duration_seconds / 60 * 150)
        
        # Theme description
        theme_description = podcast_outline.theme_description if hasattr(podcast_outline, 'theme_description') else 'Not specified'

        # Format the template with all variables
        segment_prompt = SEGMENT_DIALOGUE_TEMPLATE.format(
            podcast_title=podcast_title,
            theme_description=theme_description,
            segment_context=segment_context,
            available_speakers_prompt_str=available_speakers_prompt_str,
            invented_name=invented_name,
            speaker_id_from_segment=speaker_id_from_segment,
            real_name_of_speaker=real_name_of_speaker,
            target_word_count=target_word_count,
            persona_guidance=persona_guidance,
            source_guidance=source_guidance,
            user_custom_prompt=user_custom_prompt
        )

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
            raw_response_text = await self.generate_text_async(segment_dialogue_prompt, timeout_seconds=360)
            
            # Clean the response
            cleaned_response_text = raw_response_text.strip()
            if cleaned_response_text.startswith("```json") and cleaned_response_text.endswith("```"):
                cleaned_response_text = cleaned_response_text[7:-3].strip()
            elif cleaned_response_text.startswith("```") and cleaned_response_text.endswith("```"):
                cleaned_response_text = cleaned_response_text[3:-3].strip()
            
            # Parse the response
            parsed_json_list = json.loads(cleaned_response_text)
            parsed_json_list = self._clean_keys_recursive(parsed_json_list)
            
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
    Ensure GEMINI_API_KEY is set in your .env file in the project root.
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
    # 1. Ensure you have GEMINI_API_KEY set in your .env file in the project root.
    # 2. Navigate to the project root directory in your terminal.
    # 3. Run the script as a module: python -m app.llm_service
    asyncio.run(main_test())
