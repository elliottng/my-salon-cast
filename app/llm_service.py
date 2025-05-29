# app/llm_service.py

import google.generativeai as genai
import os
import asyncio
import logging
from dotenv import load_dotenv
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type
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
            # Log the error for debugging
            logger.error(f"Error generating text with Gemini after potential retries: {e}", exc_info=True)
            # Consider more specific error handling based on Gemini API exceptions if available
            return f"Error: Could not generate text due to: {str(e)}"

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

    async def research_persona_async(self, source_text: str, persona_focus: str = None) -> str:
        """
        Conducts persona research based on the provided source text.
        Allows for specifying a focus for the persona research.
        """
        if not source_text:
            raise ValueError("Source text for persona research cannot be empty.")

        if persona_focus:
            prompt = (
                f"Based on the following text, conduct research for a persona. "
                f"Focus specifically on: {persona_focus}.\n\n"
                "Describe the persona's likely demographics, interests, viewpoints, "
                "and communication style as suggested by the text.\n\n"
                f"---\n{source_text}\n---"
            )
        else:
            # Default persona research prompt
            prompt = (
                "Based on the following text, develop a detailed persona. "
                "Consider the likely demographics, interests, values, pain points, "
                "and communication style of an individual who would resonate with or be represented by this text. "
                "Provide a narrative description of this persona.\n\n"
                f"---\n{source_text}\n---"
            )
        
        return await self.generate_text_async(prompt)

    async def generate_podcast_outline_async(
        self,
        source_analyses: list[str],
        persona_research_docs: list[str],
        desired_podcast_length_str: str,
        num_prominent_persons: int,
        names_prominent_persons_list: list[str],
        user_provided_custom_prompt: str = None
    ) -> str:
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
            
            # Format Persona Research Documents for PRD prompt
            formatted_persona_research_str_parts = []
            if persona_research_docs:
                for i, doc in enumerate(persona_research_docs):
                    formatted_persona_research_str_parts.append(f"Persona Research Document {i+1}:\\n{doc}\\n---")
            else:
                formatted_persona_research_str_parts.append("No persona research documents provided.")

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

Provide the outline in a clear, hierarchical format (e.g., Markdown with headings and nested bullets).
Clearly indicate which named persona (or generic role) is intended to voice specific points or lead particular exchanges.
"""
            final_prompt = prd_outline_prompt_template.format(
                input_formatted_source_analyses_str="\\n".join(formatted_source_analyses_str_parts),
                input_formatted_persona_research_str="\\n".join(formatted_persona_research_str_parts),
                input_desired_podcast_length_str=desired_podcast_length_str,
                input_num_prominent_persons=num_prominent_persons,
                input_formatted_names_prominent_persons_str=formatted_names_prominent_persons_str
            )

        return await self.generate_text_async(final_prompt)

    async def generate_dialogue_async(
        self,
        podcast_outline: str,
        source_analyses: list[str],
        persona_research_docs: list[str],
        desired_podcast_length_str: str, # e.g., "10 minutes"
        num_prominent_persons: int,
        # List of tuples: (prominent_person_name, follower_name_initial, follower_system_assigned_gender)
        # e.g., [("Cardano Ada", "C", "Female"), ("Polkadot Gavin", "P", "Male")]
        prominent_persons_details: list[tuple[str, str, str]], 
        user_provided_custom_prompt: str = None # Optional, for future flexibility
    ) -> str:
        """
        Generates the full podcast dialogue script based on the outline and other inputs,
        using the prompt defined in PRD Section 4.2.5.1.
        """
        if user_provided_custom_prompt:
            final_dialogue_prompt = user_provided_custom_prompt # Or integrate it if needed
            # For now, if custom prompt is given, we assume it's complete and self-contained
            # or that it contains its own placeholders for the data below if needed.
            # This part might need refinement based on how custom prompts are intended to be used.
        else:
            # Format Source Analyses
            formatted_source_analyses_str_parts = []
            if source_analyses:
                for i, doc in enumerate(source_analyses):
                    formatted_source_analyses_str_parts.append(f"Source Analysis Document {i+1}:\n{doc}\n---")
            else:
                formatted_source_analyses_str_parts.append("No source analysis documents provided.")
            formatted_source_analyses_str = "\n".join(formatted_source_analyses_str_parts)

            # Format Persona Research Documents
            formatted_persona_research_str_parts = []
            if persona_research_docs:
                for i, doc in enumerate(persona_research_docs):
                    formatted_persona_research_str_parts.append(f"Persona Research Document {i+1}:\n{doc}\n---")
            else:
                formatted_persona_research_str_parts.append("No persona research documents provided.")
            formatted_persona_research_str = "\n".join(formatted_persona_research_str_parts)

            # Format Prominent Persons Details
            # This tells the LLM about each prominent person, their follower's name initial, and system-assigned gender.
            formatted_prominent_persons_details_parts = []
            if num_prominent_persons > 0 and prominent_persons_details:
                for i, (name, initial, gender) in enumerate(prominent_persons_details):
                    formatted_prominent_persons_details_parts.append(
                        f"  Prominent Person {i+1}: {name}\n"
                        f"    - Follower Name Initial: {initial}\n"
                        f"    - Follower System-Assigned Gender: {gender}"
                    )
                formatted_prominent_persons_details_str = "Details for Prominent Persons and their Followers:\n" + "\n".join(formatted_prominent_persons_details_parts)
            else:
                formatted_prominent_persons_details_str = "No prominent persons specified. Dialogue will be between Host and potentially a generic Analyst/Expert."

            # PRD 4.2.5.1 Dialogue Writing Prompt Template
            prd_dialogue_prompt_template = """Based on all the provided inputs, write the full dialogue script.
Key Instructions & Guidelines:
Adherence to Outline:

The Podcast Outline Document is the primary source. Follow its structure, flow, assigned speakers for particular points, and integrate any specific instructions it contains (e.g., how to introduce topics, sequence debates, or reference evidence).
Ensure all thematic segments from the outline are covered in the dialogue. You have discretion to focus on more interesting themes at the expense of less interesting themes.
Dialogue Style:

Conversational & Engaging: The dialogue should flow naturally, like a real conversation. Avoid overly formal or robotic language.
Informative: Accurately reflect the key information from the Source Analysis Documents as guided by the outline.
Entertaining: Where appropriate and consistent with the topic and personas, inject elements that make the podcast enjoyable to listen to.
Viewpoint-Driven: Speakers, especially followers, must express views consistent with their researched personas or assigned roles. The dialogue should highly viewpoint diversity through healthy debate.
Speaker Roles & Dialogue:

Host:
The Host guides the conversation, introduces topics and segments as per the outline, provides necessary narration or summaries of source information, and facilitates discussions.
Ensure the Host's dialogue is clear and helps maintain the podcast's structure.
Follower Speakers (if prominent persons were specified):
Name Generation: For each follower speaker, you must generate a first name. This name MUST start with the provided Initial and MUST be congruent with the System-Assigned Gender provided for that follower. (e.g., If Initial is 'A' and System-Assigned Gender is 'Female', a name like 'Alice' or 'Anna' would be appropriate).
Introduction: The Host will introduce these speakers as followers/advocates of the prominent person's viewpoints (e.g., "Joining us is [Follower's Generated Name], who will be sharing insights reflecting [Prominent Person]'s perspectives...").
Content: Their dialogue must strongly and accurately reflect the viewpoints, opinions, and characteristic speaking style of the prominent person they represent, drawing from the Persona Research Document and as cued by the Podcast Outline.
Attribution: Ensure their lines are clearly attributable to their generated first name (e.g., "[Generated Follower Name]:").
Generic Speakers (if no prominent persons were specified):
If the outline includes roles like 'Analyst' or 'Expert' in addition to the Host, write their dialogue to be informative and engaging, fulfilling the purpose outlined for them.
Integrating Content & Discussions:

Seamlessly weave in facts, data, or educational points from the Source Analysis Documents when the outline calls for it.
If the outline details a debate or discussion between speakers, create dynamic and robust exchanges that allow for the strong expression of differing standpoints, while keeping the discussion constructive and focused.
Clarity of Representation:

The dialogue must make it clear which prominent person's viewpoint a follower represents, or what the role of a generic speaker is.
Length Adherence:

The total word count of the script should closely target the user's specified podcast duration, calculated at approximately 150 words per minute. You have discretion to manage the depth of discussion for each outline point accordingly.
Output Format Requirements:
Provide the output as a clean dialogue script.
Each line of dialogue must start with the speaker's name (e.g., "Host:", "[Generated Follower Name]:", "Analyst:") followed by a colon and then the spoken text.
Ensure clear delineation between speakers.

Inputs for Dialogue Generation:

1. Podcast Outline Document:
{podcast_outline}

2. Source Analysis Documents (for contextual reference):
{formatted_source_analyses}

3. Persona Research Documents (for contextual reference and follower dialogue):
{formatted_persona_research}

4. Desired Podcast Length:
{desired_podcast_length_str}

5. Prominent Persons Information (if any):
{formatted_prominent_persons_details}

Now, please generate the dialogue script based on all the above.
"""
            final_dialogue_prompt = prd_dialogue_prompt_template.format(
                podcast_outline=podcast_outline,
                formatted_source_analyses=formatted_source_analyses_str,
                formatted_persona_research=formatted_persona_research_str,
                desired_podcast_length_str=desired_podcast_length_str,
                formatted_prominent_persons_details=formatted_prominent_persons_details_str
            )

        return await self.generate_text_async(final_dialogue_prompt)

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
        persona_research_result = await service.research_persona_async(sample_text_for_analysis)
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
