import pytest
import asyncio
import json
import os
import re
from unittest.mock import Mock, patch, AsyncMock # AsyncMock might not be directly used by these specific tests but good for consistency if fixture evolves

from app.llm_service import GeminiService

# Check if the API key is available in the environment for integration tests
GEMINI_API_KEY_AVAILABLE = bool(os.environ.get("GEMINI_API_KEY"))

# Content from test_article.txt
TEST_ARTICLE_CONTENT = """The Future of Artificial Intelligence in Healthcare

Artificial intelligence (AI) is rapidly transforming the healthcare industry, promising to improve patient outcomes while reducing costs. From diagnostic tools to personalized treatment plans, AI applications are beginning to demonstrate real-world benefits across medical specialties.

Recent Developments in AI Healthcare

One of the most promising areas of AI in healthcare is medical imaging analysis. Machine learning algorithms have shown remarkable accuracy in detecting abnormalities in X-rays, MRIs, and CT scans. In some studies, AI systems have matched or even exceeded the performance of experienced radiologists in detecting conditions like pneumonia, breast cancer, and retinal diseases.

Predictive analytics is another field where AI is making significant strides. By analyzing vast amounts of patient data, AI systems can identify patients at high risk for certain conditions, allowing for early intervention. For example, algorithms can now predict which patients are likely to develop sepsis—a life-threatening condition—hours before traditional clinical signs would trigger an alert.

Virtual health assistants and chatbots are becoming increasingly sophisticated, providing patients with 24/7 access to medical guidance. These tools can triage symptoms, schedule appointments, and even monitor chronic conditions by regularly checking in with patients.

Challenges and Concerns

Despite the promise, AI in healthcare faces significant hurdles. Data privacy concerns are paramount, as AI systems require vast amounts of sensitive patient information to function effectively. Healthcare organizations must balance innovation with strict adherence to regulations like HIPAA in the United States and GDPR in Europe.

The \"black box\" problem—where AI makes decisions through processes that humans cannot easily interpret—raises ethical questions about accountability and transparency. If an AI system recommends a treatment plan, who is responsible if that recommendation proves harmful?

There's also the risk of algorithmic bias. If training data isn't sufficiently diverse, AI systems may perform better for certain demographic groups than others, potentially exacerbating existing healthcare disparities.

The Human Element

Many healthcare professionals worry that the rush to adopt AI might overlook the importance of the human touch in medicine. The doctor-patient relationship, built on empathy and trust, remains a cornerstone of effective healthcare. AI should augment, not replace, this critical human connection.

Dr. Maria Chen, a cardiologist at University Medical Center, notes: \"AI tools help me analyze data more efficiently, but they don't replace my clinical judgment or my ability to understand what matters most to my patients as individuals.\"

Future Outlook

Experts predict that the integration of AI into healthcare will continue to accelerate. The global market for AI in healthcare is expected to reach $45.2 billion by 2026, growing at an annual rate of 44.9%. Investments are pouring in from both established healthcare companies and tech giants like Google, Microsoft, and Amazon.

Regulatory frameworks are evolving to address the unique challenges posed by AI in medicine. The FDA has begun approving AI-based medical devices through its Digital Health Software Precertification Program, signaling a pathway for bringing these innovations to market.

Conclusion

The future of AI in healthcare looks promising but requires careful navigation of technical, ethical, and human considerations. When implemented thoughtfully, AI has the potential to democratize access to quality healthcare, empower patients with better information, and free healthcare providers to focus on the aspects of care that require uniquely human skills.

As we stand at this technological crossroads, one thing is clear: AI will not replace healthcare professionals, but healthcare professionals who use AI effectively may replace those who don't."""

SAMPLE_ANALYSIS_PROMPT = f"""Please analyze the following text and provide your analysis in JSON format. 
The JSON object should have exactly two keys: 'summary_points' and 'detailed_analysis'.
- 'summary_points' should be a list of strings, where each string is a key summary point from the text.
- 'detailed_analysis' should be a single string containing a more in-depth, free-form textual analysis of the source content.

Example JSON format:
{{
  \"summary_points\": [\"Key takeaway 1\", \"Important fact 2\", \"Main argument 3\"],
  \"detailed_analysis\": \"The text discusses [topic] with a [tone/style]. It presents arguments such as [argument A] and [argument B], supported by [evidence]. The overall sentiment appears to be [sentiment]. Noteworthy stylistic features include [feature X]...\"
}}

Analyze this text:
---
{TEST_ARTICLE_CONTENT}
---
"""

@pytest.fixture
def gemini_service():
    return GeminiService()

# --- Tests for generate_text_async --- 

@pytest.mark.asyncio
async def test_generate_text_async_success_multipart_response(gemini_service):
    mock_response_part1 = Mock()
    mock_response_part1.text = "Hello "
    mock_response_part2 = Mock()
    mock_response_part2.text = "World!"
    
    mock_api_response = Mock()
    mock_api_response.parts = [mock_response_part1, mock_response_part2]
    mock_api_response.text = None # Ensure parts are used

    with patch.object(gemini_service.model, 'generate_content', return_value=mock_api_response) as mock_generate_content:
        result = await gemini_service.generate_text_async("test prompt")
        mock_generate_content.assert_called_once_with("test prompt")
        assert result == "Hello World!"

@pytest.mark.asyncio
async def test_generate_text_async_success_single_text_response(gemini_service):
    mock_api_response = Mock()
    mock_api_response.parts = [] # Ensure text attribute is used
    mock_api_response.text = "Hello Single World!"

    with patch.object(gemini_service.model, 'generate_content', return_value=mock_api_response) as mock_generate_content:
        result = await gemini_service.generate_text_async("test prompt")
        mock_generate_content.assert_called_once_with("test prompt")
        assert result == "Hello Single World!"

@pytest.mark.asyncio
async def test_generate_text_async_empty_prompt(gemini_service):
    with pytest.raises(ValueError) as excinfo:
        await gemini_service.generate_text_async("")
    assert "Prompt cannot be empty" in str(excinfo.value)

@pytest.mark.asyncio
async def test_generate_text_async_timeout(gemini_service):
    with patch.object(gemini_service.model, 'generate_content', side_effect=asyncio.TimeoutError("Simulated API timeout")) as mock_generate_content:
        # Let's try mocking asyncio.wait_for to raise TimeoutError directly for this specific test
        with patch('asyncio.wait_for', side_effect=asyncio.TimeoutError) as mock_wait_for:
            result = await gemini_service.generate_text_async(SAMPLE_ANALYSIS_PROMPT, timeout_seconds=0.1)
            mock_wait_for.assert_called_once()
            assert "Gemini API timeout" in result
            assert "API call timed out after 0.1 seconds" in result

@pytest.mark.asyncio
async def test_generate_text_async_no_text_content(gemini_service):
    mock_api_response = Mock()
    mock_api_response.parts = []
    mock_api_response.text = None
    mock_api_response.prompt_feedback = None

    with patch.object(gemini_service.model, 'generate_content', return_value=mock_api_response) as mock_generate_content:
        result = await gemini_service.generate_text_async(SAMPLE_ANALYSIS_PROMPT)
        mock_generate_content.assert_called_once_with(SAMPLE_ANALYSIS_PROMPT)
        assert result == "Error: No text content in Gemini response or response was blocked."

@pytest.mark.asyncio
async def test_generate_text_async_prompt_feedback_block(gemini_service):
    mock_feedback = Mock()
    mock_feedback.block_reason = "SAFETY"
    mock_feedback.safety_ratings = [Mock(category="HARM_CATEGORY_SEXUAL", probability="HIGH")]
    
    mock_api_response = Mock()
    mock_api_response.parts = []
    mock_api_response.text = None
    mock_api_response.prompt_feedback = mock_feedback

    with patch.object(gemini_service.model, 'generate_content', return_value=mock_api_response) as mock_generate_content:
        result = await gemini_service.generate_text_async(SAMPLE_ANALYSIS_PROMPT)
        mock_generate_content.assert_called_once_with(SAMPLE_ANALYSIS_PROMPT)
        assert f"Error: Could not generate text. Prompt feedback: {mock_feedback}" in result

@pytest.mark.asyncio
async def test_generate_text_async_api_error(gemini_service):
    # Mocking a non-retryable error or an error after retries are exhausted
    with patch.object(gemini_service.model, 'generate_content', side_effect=RuntimeError("Simulated API error")) as mock_generate_content:
        with pytest.raises(RuntimeError) as excinfo:
            await gemini_service.generate_text_async(SAMPLE_ANALYSIS_PROMPT)
        mock_generate_content.assert_called_once_with(SAMPLE_ANALYSIS_PROMPT)
        assert "Failed to generate text due to an unexpected error: Simulated API error" in str(excinfo.value)

@pytest.mark.asyncio
async def test_gta_for_source_analysis(gemini_service):
    """Tests generate_text_async when called with a prompt similar to analyze_source_text_async."""
    # SAMPLE_ANALYSIS_PROMPT already uses TEST_ARTICLE_CONTENT and the full default prompt template
    prompt_to_use = SAMPLE_ANALYSIS_PROMPT
    
    expected_data = {
        "summary_points": ["Mock summary point 1", "Mock summary point 2"],
        "detailed_analysis": "This is a mock detailed analysis of the article."
    }
    expected_json_output = json.dumps(expected_data)

    # Mock the underlying API call's response object
    mock_api_response_obj = Mock()
    mock_api_response_obj.parts = [] # Ensure .text is used
    mock_api_response_obj.text = expected_json_output

    with patch.object(gemini_service.model, 'generate_content', return_value=mock_api_response_obj) as mock_generate_content_actual_api:
        result_str = await gemini_service.generate_text_async(prompt_to_use)
        
        mock_generate_content_actual_api.assert_called_once_with(prompt_to_use)
        assert result_str == expected_json_output
        
        # Verify the result is valid JSON and matches the expected structure
        loaded_result = json.loads(result_str)
        assert loaded_result["summary_points"] == expected_data["summary_points"]
        assert loaded_result["detailed_analysis"] == expected_data["detailed_analysis"]


@pytest.mark.integration
@pytest.mark.skipif(not GEMINI_API_KEY_AVAILABLE, reason="GEMINI_API_KEY environment variable not set")
@pytest.mark.asyncio
async def test_generate_text_async_integration_source_analysis_format(gemini_service):
    """
    Integration test: Calls the actual Gemini API with a prompt
    expecting SourceAnalysis-like JSON output.
    """
    prompt_to_use = SAMPLE_ANALYSIS_PROMPT # Uses TEST_ARTICLE_CONTENT

    try:
        # No mocking here - direct call
        result_str = await gemini_service.generate_text_async(prompt_to_use, timeout_seconds=180) # Longer timeout for real call

        assert isinstance(result_str, str), "API response should be a string"
        assert len(result_str) > 0, "API response should not be empty"

        cleaned_json_str = result_str
        # Try to extract JSON from markdown code block
        # This regex handles ```json ... ``` or ``` ... ```
        match = re.search(r"```(?:json)?\s*(\{[\s\S]*?\})\s*```", result_str)
        if match:
            cleaned_json_str = match.group(1)
        else:
            # Fallback for plain JSON or if LLM doesn't use markdown, strip whitespace
            cleaned_json_str = result_str.strip()

        try:
            print(f"\n--- API Response (Cleaned JSON) ---\n{cleaned_json_str}\n--- End API Response ---") # Print for inspection
            loaded_json = json.loads(cleaned_json_str)
        except json.JSONDecodeError as e:
            original_response_snippet = result_str[:500] if result_str else "[empty response]"
            cleaned_response_snippet = cleaned_json_str[:500] if cleaned_json_str else "[empty cleaned response]"
            pytest.fail(
                f"API response could not be parsed as valid JSON after cleaning attempt: {e}\n"
                f"Original response (first 500 chars): {original_response_snippet}...\n"
                f"Cleaned response for parsing (first 500 chars): {cleaned_response_snippet}..."
            )

        assert isinstance(loaded_json, dict), "Parsed JSON should be a dictionary"

        assert "summary_points" in loaded_json, "JSON response must contain 'summary_points'"
        assert isinstance(loaded_json["summary_points"], list), "'summary_points' should be a list"
        # We can't assert specific content for summary_points, but we can check type if not empty
        if loaded_json["summary_points"]:
            for item in loaded_json["summary_points"]:
                assert isinstance(item, str), "Each item in 'summary_points' should be a string"

        assert "detailed_analysis" in loaded_json, "JSON response must contain 'detailed_analysis'"
        assert isinstance(loaded_json["detailed_analysis"], str), "'detailed_analysis' should be a string"
        assert len(loaded_json["detailed_analysis"]) > 0, "'detailed_analysis' should not be empty if present"

    except asyncio.TimeoutError:
        pytest.fail("The API call timed out during the integration test.")
    except Exception as e:
        # Catch other potential errors like API connection issues, etc.
        pytest.fail(f"An unexpected error occurred during the integration test: {e}\nResponse (first 500 chars): {result_str[:500]}...")
