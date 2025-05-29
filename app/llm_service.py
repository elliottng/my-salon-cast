# app/llm_service.py

import google.generativeai as genai
import os
import asyncio
import logging
from dotenv import load_dotenv
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type
import json # For potential JSONDecodeError
from typing import List, Optional
from .podcast_models import PersonaResearch, PodcastOutline, DialogueTurn, SourceAnalysis # Assuming podcast_models.py is in the same app directory
from pydantic import ValidationError
from .common_exceptions import LLMProcessingError

from google.api_core.exceptions import (
    DeadlineExceeded,
    ServiceUnavailable,
    ResourceExhausted,
    InternalServerError
)

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
    async def generate_text_async(self, prompt: str) -> str:
        """
        Asynchronously generates text based on the given prompt using the configured Gemini model.
        """
        if not prompt:
            raise ValueError("Prompt cannot be empty.")
            
        try:
            # Use asyncio.to_thread to run the blocking SDK call in a separate thread
            response = await asyncio.to_thread(self.model.generate_content, prompt)
            
            # Check for response.parts for potentially multi-part responses
            if response.parts:
                # Ensure all parts are concatenated, checking if they have a 'text' attribute
                return "".join(part.text for part in response.parts if hasattr(part, 'text'))
            # Fallback if response.text is directly available (older API versions or simpler responses)
            elif hasattr(response, 'text') and response.text:
                 return response.text
            else:
                # This case might occur if the response is blocked, has no text content, or an unexpected structure
                # Log the full response for debugging if possible.
                # print(f"Gemini response issue. Full response: {response}")
                # Check for prompt feedback which might indicate blocking
                if hasattr(response, 'prompt_feedback') and response.prompt_feedback:
                    return f"Error: Could not generate text. Prompt feedback: {response.prompt_feedback}"
                return "Error: No text content in Gemini response or response was blocked."

        except Exception as e:
            # This is a general catch-all for any other errors during the API call or response processing.
            logger.error(f"Unexpected error in generate_text_async: {e.__class__.__name__} - {e}", exc_info=True)
            # Ensure an exception is raised so the caller knows something went wrong.
            raise RuntimeError(f"Failed to generate text due to an unexpected error: {e}") from e

    async def analyze_source_text_async(self, source_text: str, analysis_instructions: str = None) -> str:
        """
        Analyzes the provided source text using the LLM.
        Allows for custom analysis instructions.
        """
        if not source_text:
            raise ValueError("Source text for analysis cannot be empty.")

        if analysis_instructions:
            prompt = f"{analysis_instructions}\n\nAnalyze the following text:\n\n---\n{source_text}\n---"
        else:
            # Default analysis prompt
            prompt = (
                "Please analyze the following text. Identify the key topics, main arguments, "
                "the overall sentiment, and any notable stylistic features. "
                "Provide a concise summary of your analysis.\n\n"
                f"---\n{source_text}\n---"
            )
        
        return await self.generate_text_async(prompt)

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

            # PRD 4.2.4 Prompt Template
            prd_outline_prompt_template = """LLM Prompt: Podcast Outline Generation
Role: You are an expert podcast script developer and debate moderator. Your primary objective is to create a comprehensive, engaging, and informative podcast outline based on the provided materials.

Overall Podcast Goals:

Educate: Clearly summarize and explain the key topics, findings, and information presented in the source documents for an audience of intellectually curious professionals.
Explore Perspectives: If prominent persons are specified, the podcast must clearly articulate their known viewpoints and perspectives on the topics, drawing from their provided persona research documents.
Facilitate Insightful Discussion/Debate: If these prominent persons have differing opinions, or if source materials present conflicting yet important viewpoints, the podcast should feature a healthy, robust debate and discussion, allowing for strong expression of these differing standpoints.

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
                # Clean keys before parsing, as Gemini sometimes adds extra spaces
                parsed_json_dict = json.loads(cleaned_response_text)
                parsed_json_dict = GeminiService._clean_keys_recursive(parsed_json_dict) 

                podcast_outline = PodcastOutline(**parsed_json_dict)
                logger.info(f"Successfully generated and validated podcast outline: {podcast_outline.title_suggestion}")
                return podcast_outline
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
        """
        # Placeholder for the actual PRD dialogue prompt template
        prd_dialogue_prompt_template = """
PLACEHOLDER: Define the PRD dialogue prompt template here.
It should include placeholders like {podcast_outline}, {formatted_source_analyses}, 
{formatted_persona_research}, {desired_podcast_length_str}, 
and {formatted_prominent_persons_details}.
"""
        podcast_outline_str = podcast_outline.model_dump_json(indent=2)
        formatted_source_analyses_str = json.dumps([sa.model_dump() for sa in source_analyses], indent=2)
        formatted_persona_research_str = json.dumps([prd.model_dump() for prd in persona_research_docs], indent=2)
        formatted_prominent_persons_details_str = json.dumps(prominent_persons_details, indent=2)

        logger.debug(f"PRD Dialogue Template Before Formatting:\n{prd_dialogue_prompt_template}")
        logger.debug(f"Dialogue Formatting Args - podcast_outline (type {type(podcast_outline_str)}): {podcast_outline_str[:500]}...")
        logger.debug(f"Dialogue Formatting Args - formatted_source_analyses (type {type(formatted_source_analyses_str)}): {formatted_source_analyses_str[:200]}...")
        logger.debug(f"Dialogue Formatting Args - formatted_persona_research (type {type(formatted_persona_research_str)}): {formatted_persona_research_str[:200]}...")
        logger.debug(f"Dialogue Formatting Args - desired_podcast_length_str (type {type(desired_podcast_length_str)}): {desired_podcast_length_str}")
        logger.debug(f"Dialogue Formatting Args - formatted_prominent_persons_details (type {type(formatted_prominent_persons_details_str)}): {formatted_prominent_persons_details_str[:200]}...")
        final_dialogue_prompt = prd_dialogue_prompt_template.format(
            podcast_outline=podcast_outline_str,
            formatted_source_analyses=formatted_source_analyses_str,
            formatted_persona_research=formatted_persona_research_str,
            desired_podcast_length_str=desired_podcast_length_str,
            formatted_prominent_persons_details=formatted_prominent_persons_details_str
        )

        raw_response_text = await self.generate_text_async(final_dialogue_prompt)
        # Attempt to strip markdown fences if present
        cleaned_response_text = raw_response_text.strip()
        if cleaned_response_text.startswith("```json") and cleaned_response_text.endswith("```"):
            cleaned_response_text = cleaned_response_text[7:-3].strip()
        elif cleaned_response_text.startswith("```") and cleaned_response_text.endswith("```"):
            cleaned_response_text = cleaned_response_text[3:-3].strip()
        
        try:
            parsed_json_list = json.loads(cleaned_response_text)
            parsed_json_list = GeminiService._clean_keys_recursive(parsed_json_list) 
            logger.debug(f"Attempting to create DialogueTurns. First item (cleaned) keys: {list(parsed_json_list[0].keys()) if isinstance(parsed_json_list, list) and parsed_json_list and isinstance(parsed_json_list[0], dict) else 'Not a list of dicts or empty list'}")
            if not isinstance(parsed_json_list, list):
                logger.error(f"LLM response for dialogue turns was not a JSON list. Got: {type(parsed_json_list)}")
                logger.error(f"Problematic data (cleaned): '{str(parsed_json_list)[:500]}...' ")
                logger.error(f"Problematic JSON string: '{cleaned_response_text[:500]}...' ")
                raise LLMProcessingError("LLM output for dialogue turns was not a valid JSON list.")

            dialogue_turns: List[DialogueTurn] = []
            for i, item in enumerate(parsed_json_list):
                if isinstance(item, dict):
                    logger.debug(f"Attempting to create DialogueTurn for item {i} with (cleaned) keys: {list(item.keys())}")
                    dialogue_turns.append(DialogueTurn(**item))
                else:
                    logger.error(f"Item {i} in dialogue list is not a dict: {type(item)}. Content: {str(item)[:200]}")
                    raise LLMProcessingError(f"Invalid item type in dialogue list: expected dict, got {type(item)}")
            return dialogue_turns
        except json.JSONDecodeError as e:
            logger.error(f"Failed to decode LLM response as JSON for dialogue turns. Error: {e}")
            logger.error(f"Problematic JSON string: '{cleaned_response_text[:500]}...' ")
            raise LLMProcessingError(f"LLM output for dialogue turns was not valid JSON. Error: {e}")
        except ValidationError as e:
            logger.error(f"LLM response for dialogue turns failed Pydantic validation. Error: {e}")
            logger.error(f"Cleaned response text that failed validation: '{cleaned_response_text[:500]}...' ")
            raise LLMProcessingError(f"LLM output for dialogue turns did not match expected schema. Error: {e}")
        except Exception as e:
            logger.error(f"An unexpected error occurred while processing LLM response for dialogue turns: {e}")
            logger.error(f"Raw response: '{raw_response_text[:500]}...' ")
            raise LLMProcessingError(f"Unexpected error processing LLM output for dialogue turns: {e}")

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
