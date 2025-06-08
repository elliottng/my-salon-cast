"""
LLM prompt templates for MySalonCast podcast generation.

All templates use Python .format() style placeholders like {variable_name}.
Variables are substituted at runtime in the LLM service methods.
"""

# Source text analysis prompt template
SOURCE_ANALYSIS_TEMPLATE = """You are an expert research analyst and debate coach. Your task is to analyze the provided source text and create a comprehensive and balanced briefing document that will be used by a team to prepare for a formal debate. The topic is complex and may be controversial, so your analysis must be objective, data-driven, and highlight evidence that can be used to construct multiple arguments.

Note: This briefing will be used to create an engaging podcast dialogue between historical or contemporary figures discussing this topic. Focus on extracting elements that would create compelling conversational moments.

Your final output MUST be a single JSON object. This object will contain exactly two keys: "summary_points" and "detailed_analysis".

Detailed Instructions for Each JSON Field:

1. summary_points:
This must be a JSON list of strings. Create as many summary points as needed to cover the important topics. Each string in the list should be a self-contained, substantive, and data-rich summary point that captures a critical facet of the topic. Avoid short, generic statements. Instead, craft detailed sentences that include key statistics, dates, figures, names, and outcomes directly from the source. Each point should be carefully selected to represent a cornerstone of a potential argument or a significant, undisputed fact that provides essential context.

Do: "The Battle of Jutland (31 May – 1 June 1916) resulted in greater British losses (14 ships, 6,094 casualties) compared to German losses (11 ships, 2,551 casualties), a fact the German Empire used for a tactical propaganda victory."
Don't: "The British lost more ships."

2. detailed_analysis:
This must be a single string containing a rich, free-form textual analysis of the source content, with a target length of 500-1000 words. This analysis should not merely repeat the summary points but should weave them into a larger, coherent narrative. Your primary goal here is to deconstruct the source material for a debater. You must:

- Expand on the Summary Points: Elaborate on the facts presented in the summary_points, providing the context, nuance, and background information found in the source.

- Identify Themes and Core Tensions: Structure your analysis around 3-5 central themes that could serve as natural conversation segments in a podcast. For each theme, identify the core question or tension, key evidence on multiple sides, and potential points of agreement or common ground.

- Extract Evidence for Arguments and Counterarguments: This is the most critical requirement. Explicitly identify and explain how specific facts, statistics, or statements from the source can be used to support different sides of a debate. Structure this to be directly useful for a debater. For example:
  * "To argue that Germany won a tactical victory, a debater can point to the clear disparity in losses of both ships and personnel, as the source states..."
  * "Conversely, to argue for a strategic British victory, a debater should emphasize that the German High Seas Fleet failed its primary objective of breaking the British blockade..."

- Highlight Debate Dynamics: Identify where the source material reveals points of genuine controversy, areas where reasonable people might interpret facts differently, and emotional or human-interest angles that could enliven discussion.

- Maintain Objectivity: Present the evidence for all potential arguments neutrally. Your role is to equip the debater, not to take a side. Use dispassionate and analytical language.

- Source Evaluation: Briefly note any apparent biases, perspectives, or limitations in the source material that debaters should be aware of.

- Quote Sparingly but Effectively: Include short, direct quotes from the source if they are particularly potent pieces of evidence.

Example JSON output:
{{
  "summary_points": [
    "The Battle of Jutland (31 May – 1 June 1916) resulted in greater British losses (14 ships, 6,094 casualties) compared to German losses (11 ships, 2,551 casualties), leading Germany to claim tactical victory despite failing to break the British naval blockade.",
    "Admiral Jellicoe's cautious strategy prioritized preserving the Grand Fleet's superiority over seeking decisive engagement, reflecting Britain's need to maintain naval dominance for imperial communications and blockade enforcement.",
    "The battle exposed critical vulnerabilities in British naval design, particularly inadequate armor on battlecruisers and dangerous cordite handling practices that led to catastrophic magazine explosions.",
    "Despite tactical setbacks, the strategic outcome favored Britain as the German High Seas Fleet never again challenged British naval supremacy, remaining largely confined to port for the war's remainder."
  ],
  "detailed_analysis": "The Battle of Jutland presents a fascinating study in the distinction between tactical and strategic victory, offering rich material for debate about military success metrics and long-term versus short-term outcomes. Three central themes emerge from the source material that could structure an engaging podcast discussion.\\n\\nFirst, the 'Victory Paradox' provides compelling debate fodder. Germany's ability to inflict heavier losses—sinking more ships and killing more sailors—gave them legitimate grounds to claim tactical success. A debater arguing for German victory can point to the stark casualty figures and superior gunnery performance. However, those arguing for British strategic victory can emphasize that naval battles aren't won by scorekeeping alone. The source reveals that Germany failed in its primary objective: breaking the blockade that was slowly strangling the German economy. This tension between immediate battle results and long-term strategic outcomes offers natural conversation dynamics.\\n\\nSecond, the 'Leadership Dilemma' theme explores contrasting command philosophies. Admiral Jellicoe's cautious approach, which the source indicates was driven by Churchill's warning that he was 'the only man who could lose the war in an afternoon,' provides rich material for discussing risk management in warfare. Defenders of Jellicoe can argue his preservation of fleet superiority was strategically sound, while critics can point to missed opportunities for decisive victory. The German aggressive tactics under Scheer, including the famous 'death ride' of the battlecruisers, offer a contrasting philosophy ripe for debate.\\n\\nThird, the 'Technological Reckoning' revealed by the battle provides technical yet accessible discussion points. The source's details about British battlecruiser vulnerabilities and unsafe cordite handling practices that led to spectacular explosions can be contrasted with German superior armor design and safety procedures. This allows for broader discussions about innovation, preparedness, and the human cost of technical failures.\\n\\nThe source material reveals potential biases toward British strategic thinking while acknowledging German tactical superiority. This balanced perspective provides debaters on both sides with credible evidence. The human drama—from individual ship stories to command decisions under pressure—offers emotional hooks to enliven what could otherwise be dry tactical discussion.\\n\\nFor podcast purposes, the battle serves as an excellent microcosm of larger WWI themes: attrition versus decision, technology versus tradition, and the gap between public perception and strategic reality. The ambiguous outcome ensures neither side has an overwhelming advantage in debate, creating natural tension and engagement opportunities."
}}

Analyze this text:
---
{source_text}
---"""

# Persona research prompt template
PERSONA_RESEARCH_TEMPLATE = """
You are a debate coach and you are preparing {person_name} for a podcast appearance. Your work will contribute to a podcast aiming to be educational, entertaining, and to highlight viewpoint diversity by authentically representing {person_name}'s perspectives.

GENDER DETERMINATION:
As a critical step, determine the gender of {person_name} based on historical facts and biographical information.
- For historical or public figures, use verified biographical information.
- For fictional characters or less documented individuals, base this on the source text.
- Assign EXACTLY ONE of these values: "male", "female", or "neutral" (for non-binary or cases with insufficient information).
- This determination will be used for voice assignment in the podcast, so accuracy is important.

IMPORTANT DISTINCTION:
You have two separate tasks:
1. First, establish a detailed profile of {person_name} based on general historical knowledge (not limited to the source text)
2. Then, have this established persona analyze and engage with the specific topics in the source text
3. When the source text contains topics with minimal obvious connection to {person_name}'s known interests:
   - First identify the underlying principles, values, or frameworks that guided their thinking
   - Then apply these fundamental principles to the new topic rather than inventing specific opinions
   - Clearly indicate the level of confidence in your extrapolations (e.g., "Based on their views on X, they would likely approach Y by...")
   - Focus on methodological similarities rather than speculating about specific technical details beyond their era

Source Text:
---
{source_text}
---

Please provide your research as a JSON object with the following structure:
{{
  "person_id": "{person_id}",
  "name": "{person_name}",
  "gender": "REQUIRED: Use verified biographical information to determine {person_name}'s gender. Assign EXACTLY one value: 'male', 'female', or 'neutral'. This is critical for voice selection.",
  "invented_name": "REQUIRED: Create a fictional first name that sounds phonetically similar to '{person_name}' or shares similar linguistic characteristics. This name will be used to identify the persona in dialogue transcripts. Choose a name that feels natural and maintains some connection to the original while being clearly distinct. For example: 'Albert Einstein' → 'Alfred', 'Marie Curie' → 'Marina', 'Isaac Newton' → 'Ivan'. The name should match the determined gender.",
  "detailed_profile": "Your detailed profile should be organized into the following five distinct sections, each clearly labeled:

  ### PART 1: PROFILE OF {person_name_upper} (250 words)
  Provide a concise biography highlighting their significance, background, key accomplishments, and historical context. This should be based on general historical knowledge, not limited to the source text. Include 1-2 authentic quotes if available with contextual explanation.

  ### PART 2: CORE VIEWPOINTS AND BELIEFS (400 words)
  Detail {person_name}'s most strongly held viewpoints, ideas, and opinions based on historical record and general knowledge. Focus on their fundamental principles, philosophical stance, and value system. Include both mainstream and controversial positions they advocated for. Preserve the authenticity of their perspectives even when they differ from contemporary views.

  ### PART 3: TOPIC ANALYSIS FROM {person_name_upper}'S PERSPECTIVE (1000 words)
  First, identify 2-6 primary topics from the source text that {person_name} would find most compelling or contentious based on their background and beliefs. These should be topics where their perspective would be most distinctive or valuable.
  
  For each identified topic:
  - Identify what aspect would interest or concern them most
  - Explain what positions they would likely take based on their known principles
  - Describe how they would frame arguments in support of these positions
  - Find the facts, figures, and statistics that most powerfully support these positions
  - Address how they might handle counterarguments
  
  For topics with minimal connection to {person_name}'s known interests:
  - Focus on how their fundamental values and thinking methods would apply
  - Draw parallels between their known positions and the unfamiliar topic
  - Identify aspects they would recognize as familiar despite the different context
  - Be transparent about the degree of extrapolation required (e.g., \"While [topic] didn't exist in their time, their approach to [analogous issue] suggests...\")
  
  If the source topics emerged after their lifetime, extrapolate their views based on their established principles and thinking patterns.

  ### PART 4: DEBATE PREPARATION AND ADVICE (250 words)
  Provide specific strategies for {person_name} to effectively communicate their positions during a podcast discussion about the source material. Include:
  - Compelling talking points they could use
  - Potential questions they might pose to other speakers
  - How to address likely challenges to their viewpoints
  - Ways to leverage their unique expertise and perspective

  ### PART 5: SPEAKING STYLE AND EXPRESSION (250 words)
  Describe {person_name}'s observed or inferred communication style based on historical accounts. Include:
  - Characteristic patterns in their rhetoric and argumentation
  - Tone and emotional qualities of their speech
  - Distinctive vocabulary, phrases, or sentence structures they favor
  - 3-5 example sentence templates that capture their authentic voice
  - How they engage with opponents or contrasting viewpoints

  Format all five parts as a single cohesive document with clear section headings."
}}}}

Important guidelines:
1. Parts 1, 2, and 5 should draw primarily from general historical knowledge about {person_name}, not from the source text.
2. Parts 3 and 4 should have the established persona engage with the specific source text content.
3. Present {person_name}'s authentic viewpoints and beliefs even if they differ from contemporary views or standards.
4. Adhere closely to the word count guidelines for each section.
5. Ensure all analysis is substantiated by known facts about {person_name} or reasonable extrapolation from their documented views.

⚠️ CRITICALLY IMPORTANT JSON FORMAT INSTRUCTIONS ⚠️ 
Your output MUST be a single, valid JSON object only, with no additional text before or after the JSON. 
- The detailed_profile field must be a simple string (not a nested object or array)
- Use proper JSON escaping for quotes and special characters in the detailed_profile string
- Do not include any markdown formatting markers like ```json or ``` in your response
- Double-check that your final output is parseable by JavaScript's JSON.parse()
"""

# Podcast outline generation prompt template  
PODCAST_OUTLINE_TEMPLATE = """LLM Prompt: Multi-Segment Podcast Outline Generation

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

⚠️ IMPORTANT ⚠️- TARGET TOTAL WORD COUNT: {calculated_total_words} words (This is a hard requirement based on the requested podcast duration of {input_desired_podcast_length_str})
Number of Prominent Persons Specified: {input_num_prominent_persons}
Names of Prominent People Specified: {input_formatted_names_prominent_persons_str}
Available Persona IDs (from Persona Research Documents, if any): {input_formatted_available_persona_ids_str}
Generic Speaker IDs available: "Host" (Invented Name: "Host", Gender: [Host's gender from persona_details_map]), "Narrator" (Typically neutral or assigned as needed)

Persona Details:
{input_formatted_persona_details_str}

Task: Generate a Multi-Segment Podcast Outline

Create a detailed, multi-segment outline for the entire podcast. This outline will serve as the blueprint for the subsequent dialogue writing step. The podcast should be divided into logical segments, each with a clear purpose and speaker focus.

Outline Structure Guidelines:

Your outline must break the podcast into several distinct segments. Each segment should contribute to the overall flow and goals. Create segments with EXACTLY these word count targets:

- Introduction/Opening Hook: {intro_words} words
  • The 'Host' must introduce any personas speaking in a segment using their 'Invented Name' and clarifying which 'Real Name' they represent.
  • For example: 'Host: Now, let's hear from Jarvis, an expert representing John Doe on this topic.'
  • This should happen when a persona is first introduced or takes a significant speaking turn in a new context.
- Deep Dive into Theme 1: {theme1_words} words (Should prominently feature one of the researched personas when available)
- Deep Dive into Theme 2: {theme2_words} words (Should prominently feature a different researched persona when available)
- Points of Agreement/Conflict: {discussion_words} words (IMPORTANT: This is the core of the podcast where the most valuable insights and engaging discussions emerge)
- Conclusion/Summary: {conclusion_words} words

⚠️ CRITICAL REQUIREMENT: The sum of all segment word counts MUST EQUAL EXACTLY {calculated_total_words} words. This directly impacts the podcast duration. Segment durations will be calculated based on these word counts, where 150 words equals approximately 1 minute of audio.

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
⚠️ PERSONA USAGE REQUIREMENT: When researched personas are available (as shown in the Persona Research Documents), the Deep Dive segments MUST feature these personas as primary speakers rather than generic speakers like "Narrator". Use "Narrator" only for transitions or when no specific persona perspective is needed.
Natural and Engaging Flow: The podcast should feel conversational and engaging throughout.
Prioritize Points of Agreement/Conflict: The most engaging and illuminating parts of the podcast often come from the segments where different viewpoints interact, either finding common ground or respectfully disagreeing. These segments should be given substantial word count allocation (40-50% of total) to allow for thorough exploration of different perspectives.
Length Adherence: The sum of all segment 'target_word_count' values MUST EXACTLY EQUAL {calculated_total_words} words. This is a non-negotiable constraint. Distribute content appropriately across segments to meet this total word count.
⚠️ CRITICALLY IMPORTANT: DETAILED CONTENT CUES ⚠️
Each segment's content_cue MUST be EXTREMELY comprehensive (MINIMUM 300 WORDS, NO EXCEPTIONS) and specific, including: 
   - Key talking points in detail
   - Questions or controversies to be addressed
   - Specific facts, figures, and statistics to include
   - Important insights, theories, beliefs or arguments
   - Dialog flow and transitions
   - References to source material where relevant
   Content cues shorter than 300 words will be rejected as insufficient. The content_cue serves as a detailed blueprint for the segment and MUST be thorough enough that another writer could create the same segment based solely on your cue.

Output Format:

⚠️ CRITICALLY IMPORTANT ⚠️
You MUST include BOTH the "target_word_count" AND "estimated_duration_seconds" fields for EACH segment. This is a non-negotiable requirement.

VERY IMPORTANT: You MUST output your response as a single, valid JSON object. Do NOT use markdown formatting around the JSON.
The JSON object must conform to the following structure:
{{{{
  "title_suggestion": "string (Suggested title for the podcast episode)",
  "summary_suggestion": "string (Suggested brief summary for the podcast episode)",
  "segments": [ // THIS MUST BE A LIST OF SEGMENT OBJECTS
    {{{{
      "segment_id": "string (Unique ID for this segment, e.g., seg_01_intro)",
      "segment_title": "string (Title for this segment, e.g., Introduction to Topic X)",
      "speaker_id": "string (Identifier for the primary speaker/focus, e.g., 'Host', 'persona_john_doe')",
      "content_cue": "string (MUST be MINIMUM 300 WORDS - NO EXCEPTIONS with detailed talking points, questions, specific facts, dialog flow, and source references)",
      "target_word_count": integer (Target number of words for this segment's dialogue),
      "estimated_duration_seconds": integer (Calculated as target_word_count / 150 * 60)
    }}}}
    {{{{
      "segment_id": "string (e.g., seg_02_deepdive)",
      "segment_title": "string (e.g., Exploring Viewpoint A)",
      "speaker_id": "string (e.g., 'persona_jane_smith')",
      "content_cue": "string (MUST be MINIMUM 300 WORDS - NO EXCEPTIONS with detailed talking points, questions, specific facts, dialog flow, and source references)",
      "target_word_count": integer (Target number of words for this segment)",
      "estimated_duration_seconds": integer (Calculated from target_word_count)
    }}}}
    // ... more segments as needed ...
  ]
}}}}

Ensure all string fields are properly escaped within the JSON. The 'segments' array should contain multiple segment objects, each detailing a part of the podcast.
The `speaker_id` in each segment MUST be chosen from the persona IDs provided in the 'Persona Research Documents' (use their 'person_id' field) or be 'Host' or 'Narrator'.
"""

# Segment dialogue generation prompt template
SEGMENT_DIALOGUE_TEMPLATE = """
LLM Prompt: Podcast Segment Dialogue Generation

Role: You are an expert podcast dialogue writer. Your task is to create natural, engaging dialogue for a specific segment of a podcast.

Podcast Information:
- Title: {podcast_title}
- Overall Theme: {theme_description}

Current Segment Details:
{segment_context}

{available_speakers_prompt_str}

Instructions:
1. Write dialogue ONLY for this specific segment. The dialogue should directly address the content described in the segment's content cue.
2. The primary speaker for this segment should be {invented_name} (who is speaker ID: {speaker_id_from_segment}, representing the views of {real_name_of_speaker}). Ensure their dialogue reflects their role.
3. Include appropriate responses or questions from other speakers as needed for natural conversation flow.
4. The dialogue should be approximately {target_word_count} words in length.
5. Ensure the dialogue has a clear beginning and end appropriate for this segment's position in the overall podcast.

{persona_guidance}

{source_guidance}

Output Format:
Provide the dialogue as a JSON array of dialogue turn objects. Each object should have:
- "turn_id": A sequential number starting from the provided current_turn_id
- "speaker_id": The ID of the speaker (e.g., "Host", "john-doe", "narrator"). This MUST be the actual person_id or generic role ID.
- "text": The spoken dialogue text
- "source_mentions": An array of source reference strings (can be empty if no direct citations)

Example format:
[{{"turn_id": 1, "speaker_id": "Host", "text": "Welcome to our discussion on...", "source_mentions": []}},
 {{"turn_id": 2, "speaker_id": "john-doe", "text": "I believe that...", "source_mentions": ["Article: The Future of AI"]}}]

{user_custom_prompt}
"""
