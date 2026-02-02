"""AI-powered summarization component for generating article summaries."""
import logging
from dataclasses import dataclass
from enum import Enum
from typing import Optional
import openai


logger = logging.getLogger(__name__)


class AIProvider(Enum):
    """Supported AI providers."""
    OPENAI = "openai"
    CLAUDE = "claude"
    GEMINI = "gemini"
    GROQ = "groq"


@dataclass
class Summary:
    """Result of AI summarization operation."""
    text: str
    word_count: int
    success: bool
    error_message: Optional[str]


class AISummarizer:
    """Generates AI-powered summaries of article content."""
    
    def __init__(self, api_key: str, provider: AIProvider = AIProvider.OPENAI, model: Optional[str] = None):
        """Initialize the AISummarizer.
        
        Args:
            api_key: API key for the AI provider
            provider: AI provider to use (default: OpenAI)
            model: Specific model to use (optional, uses provider default if not specified)
        """
        self.api_key = api_key
        self.provider = provider
        
        # Set default models for each provider
        if model:
            self.model = model
        else:
            if provider == AIProvider.OPENAI:
                self.model = "gpt-3.5-turbo"
            elif provider == AIProvider.CLAUDE:
                self.model = "claude-3-haiku-20240307"
            elif provider == AIProvider.GEMINI:
                self.model = "gemini-pro"
            elif provider == AIProvider.GROQ:
                self.model = "llama-3.3-70b-versatile"
        
        # Initialize the appropriate client
        if provider == AIProvider.OPENAI:
            self.client = openai.OpenAI(api_key=api_key)
        elif provider == AIProvider.CLAUDE:
            try:
                import anthropic
                self.client = anthropic.Anthropic(api_key=api_key)
            except ImportError:
                logger.error("anthropic package not installed. Install with: pip install anthropic")
                raise
        elif provider == AIProvider.GEMINI:
            try:
                import google.generativeai as genai
                genai.configure(api_key=api_key)
                self.client = genai
            except ImportError:
                logger.error("google-generativeai package not installed. Install with: pip install google-generativeai")
                raise
        elif provider == AIProvider.GROQ:
            try:
                from groq import Groq
                self.client = Groq(api_key=api_key)
            except ImportError:
                logger.error("groq package not installed. Install with: pip install groq")
                raise
    
    def summarize(self, content: str, max_words: int = 40) -> Summary:
        """Generate a summary of the article content.
        
        Args:
            content: Full article text to summarize
            max_words: Maximum word count for summary (default: 40)
            
        Returns:
            Summary with generated text and success status
        """
        try:
            # Build the prompt
            prompt = self._build_prompt(content, max_words)
            
            # Call the appropriate AI provider
            if self.provider == AIProvider.OPENAI:
                summary_text = self._summarize_with_openai(prompt)
            elif self.provider == AIProvider.CLAUDE:
                summary_text = self._summarize_with_claude(prompt)
            elif self.provider == AIProvider.GEMINI:
                summary_text = self._summarize_with_gemini(prompt)
            elif self.provider == AIProvider.GROQ:
                summary_text = self._summarize_with_groq(prompt)
            else:
                raise ValueError(f"Unsupported provider: {self.provider}")
            
            # Validate word count
            word_count = len(summary_text.split())
            
            if not self._validate_length(summary_text, max_words):
                logger.warning(f"Summary word count ({word_count}) outside acceptable range (30-{max_words})")
            
            logger.info(f"Successfully generated summary with {word_count} words")
            return Summary(
                text=summary_text,
                word_count=word_count,
                success=True,
                error_message=None
            )
        
        except Exception as e:
            error_msg = f"AI summarization failed: {str(e)}"
            logger.error(error_msg)
            return Summary(
                text="",
                word_count=0,
                success=False,
                error_message=error_msg
            )
    
    def _build_prompt(self, content: str, max_words: int) -> str:
        """Build the prompt for AI summarization.
        
        Args:
            content: Article content to summarize
            max_words: Maximum word count
            
        Returns:
            Formatted prompt string
        """
        # Truncate content if too long (to avoid token limits)
        max_content_length = 4000
        if len(content) > max_content_length:
            content = content[:max_content_length] + "..."
        
        prompt = f"""Summarize the following news article in exactly 30-40 words.
Focus on key facts and main points. Use either a short paragraph or bullet points.

Article:
{content}

Summary:"""
        
        return prompt
    
    def _validate_length(self, summary: str, max_words: int) -> bool:
        """Validate that summary word count is within acceptable range.
        
        Args:
            summary: Generated summary text
            max_words: Maximum word count
            
        Returns:
            True if word count is between 30 and max_words (inclusive)
        """
        word_count = len(summary.split())
        return 30 <= word_count <= max_words
    
    def _summarize_with_openai(self, prompt: str) -> str:
        """Generate summary using OpenAI API.
        
        Args:
            prompt: Formatted prompt
            
        Returns:
            Generated summary text
        """
        response = self.client.chat.completions.create(
            model=self.model,
            messages=[
                {"role": "system", "content": "You are a helpful assistant that summarizes news articles concisely."},
                {"role": "user", "content": prompt}
            ],
            temperature=0.7,
            max_tokens=100
        )
        
        return response.choices[0].message.content.strip()
    
    def _summarize_with_claude(self, prompt: str) -> str:
        """Generate summary using Claude API.
        
        Args:
            prompt: Formatted prompt
            
        Returns:
            Generated summary text
        """
        response = self.client.messages.create(
            model=self.model,
            max_tokens=100,
            messages=[
                {"role": "user", "content": prompt}
            ]
        )
        
        return response.content[0].text.strip()
    
    def _summarize_with_gemini(self, prompt: str) -> str:
        """Generate summary using Gemini API.
        
        Args:
            prompt: Formatted prompt
            
        Returns:
            Generated summary text
        """
        model = self.client.GenerativeModel(self.model)
        response = model.generate_content(prompt)
        
        return response.text.strip()
    
    def _summarize_with_groq(self, prompt: str) -> str:
        """Generate summary using Groq API.
        
        Args:
            prompt: Formatted prompt
            
        Returns:
            Generated summary text
        """
        response = self.client.chat.completions.create(
            model=self.model,
            messages=[
                {"role": "system", "content": "You are a helpful assistant that summarizes news articles concisely."},
                {"role": "user", "content": prompt}
            ],
            temperature=0.7,
            max_tokens=100
        )
        
        return response.choices[0].message.content.strip()
