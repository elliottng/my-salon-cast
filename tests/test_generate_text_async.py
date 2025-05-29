import pytest
import asyncio
from unittest.mock import Mock, patch, AsyncMock # AsyncMock might not be directly used by these specific tests but good for consistency if fixture evolves

from app.llm_service import GeminiService

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
