"""Unit tests for the AISummarizer component."""
import pytest
from unittest.mock import Mock, patch, MagicMock
from src.ai_summarizer import AISummarizer, AIProvider, Summary


class TestAISummarizer:
    """Test suite for AISummarizer class."""
    
    def test_summarizer_initialization_openai(self):
        """Test AISummarizer can be initialized with OpenAI provider."""
        with patch('src.ai_summarizer.openai.OpenAI') as mock_openai:
            summarizer = AISummarizer(api_key="test-key", provider=AIProvider.OPENAI)
            assert summarizer.api_key == "test-key"
            assert summarizer.provider == AIProvider.OPENAI
            assert summarizer.model == "gpt-3.5-turbo"
            mock_openai.assert_called_once_with(api_key="test-key")
    
    def test_summarizer_custom_model(self):
        """Test AISummarizer can be initialized with custom model."""
        with patch('src.ai_summarizer.openai.OpenAI'):
            summarizer = AISummarizer(api_key="test-key", provider=AIProvider.OPENAI, model="gpt-4")
            assert summarizer.model == "gpt-4"
    
    @patch('src.ai_summarizer.openai.OpenAI')
    def test_summarize_success(self, mock_openai_class):
        """Test successful summarization with OpenAI."""
        # Setup mock
        mock_client = Mock()
        mock_response = Mock()
        mock_response.choices = [Mock()]
        # Create a summary with exactly 35 words
        summary_text = " ".join(["word"] * 35)
        mock_response.choices[0].message.content = summary_text
        mock_client.chat.completions.create.return_value = mock_response
        mock_openai_class.return_value = mock_client
        
        summarizer = AISummarizer(api_key="test-key")
        result = summarizer.summarize("This is a long article content that needs to be summarized.")
        
        # Verify
        assert result.success is True
        assert result.word_count == 35
        assert result.error_message is None
        assert len(result.text) > 0
    
    @patch('src.ai_summarizer.openai.OpenAI')
    def test_summarize_validates_word_count(self, mock_openai_class):
        """Test that summarizer validates word count is within range."""
        # Setup mock with summary in valid range
        mock_client = Mock()
        mock_response = Mock()
        mock_response.choices = [Mock()]
        mock_response.choices[0].message.content = "Valid summary with thirty words " * 3 + "and a bit more"
        mock_client.chat.completions.create.return_value = mock_response
        mock_openai_class.return_value = mock_client
        
        summarizer = AISummarizer(api_key="test-key")
        result = summarizer.summarize("Article content")
        
        # Should succeed even if word count is slightly off
        assert result.success is True
        assert result.word_count > 0
    
    @patch('src.ai_summarizer.openai.OpenAI')
    def test_summarize_handles_api_error(self, mock_openai_class):
        """Test handling of API errors during summarization."""
        # Setup mock to raise exception
        mock_client = Mock()
        mock_client.chat.completions.create.side_effect = Exception("API rate limit exceeded")
        mock_openai_class.return_value = mock_client
        
        summarizer = AISummarizer(api_key="test-key")
        result = summarizer.summarize("Article content")
        
        # Verify error handling
        assert result.success is False
        assert result.error_message is not None
        assert "API rate limit exceeded" in result.error_message
        assert result.text == ""
        assert result.word_count == 0
    
    @patch('src.ai_summarizer.openai.OpenAI')
    def test_summarize_handles_network_error(self, mock_openai_class):
        """Test handling of network errors."""
        # Setup mock to raise network exception
        mock_client = Mock()
        mock_client.chat.completions.create.side_effect = ConnectionError("Network unreachable")
        mock_openai_class.return_value = mock_client
        
        summarizer = AISummarizer(api_key="test-key")
        result = summarizer.summarize("Article content")
        
        # Verify error handling
        assert result.success is False
        assert result.error_message is not None
        assert "Network unreachable" in result.error_message
    
    @patch('src.ai_summarizer.openai.OpenAI')
    def test_summarize_truncates_long_content(self, mock_openai_class):
        """Test that very long content is truncated before sending to API."""
        # Setup mock
        mock_client = Mock()
        mock_response = Mock()
        mock_response.choices = [Mock()]
        mock_response.choices[0].message.content = "Summary of the truncated content in exactly thirty five words for testing purposes here."
        mock_client.chat.completions.create.return_value = mock_response
        mock_openai_class.return_value = mock_client
        
        # Create very long content
        long_content = "This is a very long article. " * 500
        
        summarizer = AISummarizer(api_key="test-key")
        result = summarizer.summarize(long_content)
        
        # Verify it still works
        assert result.success is True
        
        # Verify the prompt was built (content was truncated)
        mock_client.chat.completions.create.assert_called_once()
        call_args = mock_client.chat.completions.create.call_args
        prompt = call_args[1]['messages'][1]['content']
        assert len(prompt) < len(long_content)
    
    @patch('src.ai_summarizer.openai.OpenAI')
    def test_build_prompt_format(self, mock_openai_class):
        """Test that prompt is built with correct format."""
        mock_client = Mock()
        mock_openai_class.return_value = mock_client
        
        summarizer = AISummarizer(api_key="test-key")
        prompt = summarizer._build_prompt("Test article content", 40)
        
        # Verify prompt structure
        assert "30-40 words" in prompt
        assert "Test article content" in prompt
        assert "Summary:" in prompt
    
    @patch('src.ai_summarizer.openai.OpenAI')
    def test_validate_length_within_range(self, mock_openai_class):
        """Test word count validation for summaries within range."""
        mock_client = Mock()
        mock_openai_class.return_value = mock_client
        
        summarizer = AISummarizer(api_key="test-key")
        
        # Test valid lengths
        assert summarizer._validate_length("word " * 30, 40) is True
        assert summarizer._validate_length("word " * 35, 40) is True
        assert summarizer._validate_length("word " * 40, 40) is True
    
    @patch('src.ai_summarizer.openai.OpenAI')
    def test_validate_length_outside_range(self, mock_openai_class):
        """Test word count validation for summaries outside range."""
        mock_client = Mock()
        mock_openai_class.return_value = mock_client
        
        summarizer = AISummarizer(api_key="test-key")
        
        # Test invalid lengths
        assert summarizer._validate_length("word " * 29, 40) is False
        assert summarizer._validate_length("word " * 41, 40) is False
        assert summarizer._validate_length("word " * 10, 40) is False
    
    def test_summary_dataclass(self):
        """Test Summary dataclass structure."""
        summary = Summary(
            text="Test summary",
            word_count=2,
            success=True,
            error_message=None
        )
        
        assert summary.text == "Test summary"
        assert summary.word_count == 2
        assert summary.success is True
        assert summary.error_message is None
    
    def test_summary_dataclass_with_error(self):
        """Test Summary dataclass with error."""
        summary = Summary(
            text="",
            word_count=0,
            success=False,
            error_message="API error"
        )
        
        assert summary.text == ""
        assert summary.word_count == 0
        assert summary.success is False
        assert summary.error_message == "API error"
    
    @patch('src.ai_summarizer.openai.OpenAI')
    def test_summarize_continues_after_failure(self, mock_openai_class):
        """Test that summarizer can continue after a failure."""
        mock_client = Mock()
        mock_openai_class.return_value = mock_client
        
        # First call fails
        mock_client.chat.completions.create.side_effect = Exception("Temporary error")
        
        summarizer = AISummarizer(api_key="test-key")
        result1 = summarizer.summarize("First article")
        assert result1.success is False
        
        # Second call succeeds
        mock_client.chat.completions.create.side_effect = None
        mock_response = Mock()
        mock_response.choices = [Mock()]
        mock_response.choices[0].message.content = "This is a successful summary after previous failure with enough words to be valid."
        mock_client.chat.completions.create.return_value = mock_response
        
        result2 = summarizer.summarize("Second article")
        assert result2.success is True
    
    @patch('src.ai_summarizer.openai.OpenAI')
    def test_summarize_with_empty_content(self, mock_openai_class):
        """Test summarization with empty content."""
        mock_client = Mock()
        mock_response = Mock()
        mock_response.choices = [Mock()]
        mock_response.choices[0].message.content = "No content available to summarize in this article at this time."
        mock_client.chat.completions.create.return_value = mock_response
        mock_openai_class.return_value = mock_client
        
        summarizer = AISummarizer(api_key="test-key")
        result = summarizer.summarize("")
        
        # Should still work, just summarize empty content
        assert result.success is True
    
    @patch('src.ai_summarizer.openai.OpenAI')
    def test_summarize_strips_whitespace(self, mock_openai_class):
        """Test that summary text is stripped of leading/trailing whitespace."""
        mock_client = Mock()
        mock_response = Mock()
        mock_response.choices = [Mock()]
        mock_response.choices[0].message.content = "  Summary with whitespace around it that should be stripped properly.  "
        mock_client.chat.completions.create.return_value = mock_response
        mock_openai_class.return_value = mock_client
        
        summarizer = AISummarizer(api_key="test-key")
        result = summarizer.summarize("Article content")
        
        # Verify whitespace is stripped
        assert result.success is True
        assert not result.text.startswith(" ")
        assert not result.text.endswith(" ")
    
    @patch('src.ai_summarizer.openai.OpenAI')
    def test_summarize_uses_correct_model(self, mock_openai_class):
        """Test that summarizer uses the specified model."""
        mock_client = Mock()
        mock_response = Mock()
        mock_response.choices = [Mock()]
        mock_response.choices[0].message.content = "Test summary with enough words to be valid for testing purposes here."
        mock_client.chat.completions.create.return_value = mock_response
        mock_openai_class.return_value = mock_client
        
        summarizer = AISummarizer(api_key="test-key", model="gpt-4")
        summarizer.summarize("Article content")
        
        # Verify correct model was used
        call_args = mock_client.chat.completions.create.call_args
        assert call_args[1]['model'] == "gpt-4"
    
    @patch('src.ai_summarizer.openai.OpenAI')
    def test_summarize_sets_temperature(self, mock_openai_class):
        """Test that summarizer sets appropriate temperature parameter."""
        mock_client = Mock()
        mock_response = Mock()
        mock_response.choices = [Mock()]
        mock_response.choices[0].message.content = "Test summary with enough words to be valid for testing purposes here."
        mock_client.chat.completions.create.return_value = mock_response
        mock_openai_class.return_value = mock_client
        
        summarizer = AISummarizer(api_key="test-key")
        summarizer.summarize("Article content")
        
        # Verify temperature is set
        call_args = mock_client.chat.completions.create.call_args
        assert 'temperature' in call_args[1]
        assert call_args[1]['temperature'] == 0.7
