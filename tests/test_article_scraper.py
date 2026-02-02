"""Unit tests for the ArticleScraper component."""
import pytest
from datetime import datetime
from unittest.mock import Mock, patch, MagicMock
from src.article_scraper import ArticleScraper, ScrapedContent


class TestArticleScraper:
    """Test suite for ArticleScraper class."""
    
    def test_scraper_initialization(self):
        """Test ArticleScraper can be initialized with default timeout."""
        scraper = ArticleScraper()
        assert scraper.timeout == 30
    
    def test_scraper_custom_timeout(self):
        """Test ArticleScraper can be initialized with custom timeout."""
        scraper = ArticleScraper(timeout=60)
        assert scraper.timeout == 60
    
    @patch('src.article_scraper.Article')
    def test_scrape_success_with_newspaper3k(self, mock_article_class):
        """Test successful scraping using newspaper3k."""
        # Setup mock
        mock_article = Mock()
        mock_article.text = "This is a test article with sufficient content. " * 10
        mock_article.publish_date = datetime(2024, 1, 15, 10, 30)
        mock_article_class.return_value = mock_article
        
        scraper = ArticleScraper()
        result = scraper.scrape("https://example.com/article")
        
        # Verify
        assert result.success is True
        assert result.full_text == mock_article.text.strip()
        assert result.published_date == datetime(2024, 1, 15, 10, 30)
        assert result.error_message is None
        assert isinstance(result.scrape_timestamp, datetime)
        
        # Verify newspaper3k was called correctly
        mock_article.download.assert_called_once()
        mock_article.parse.assert_called_once()
    
    @patch('src.article_scraper.Article')
    def test_scrape_success_without_published_date(self, mock_article_class):
        """Test successful scraping when published date is not available."""
        # Setup mock
        mock_article = Mock()
        mock_article.text = "This is a test article with sufficient content. " * 10
        mock_article.publish_date = None
        mock_article_class.return_value = mock_article
        
        scraper = ArticleScraper()
        result = scraper.scrape("https://example.com/article")
        
        # Verify
        assert result.success is True
        assert result.published_date is None
        assert result.scrape_timestamp is not None
    
    @patch('src.article_scraper.requests.get')
    @patch('src.article_scraper.Article')
    def test_scrape_fallback_to_beautifulsoup(self, mock_article_class, mock_requests_get):
        """Test fallback to BeautifulSoup when newspaper3k fails."""
        # Make newspaper3k fail
        mock_article = Mock()
        mock_article.download.side_effect = Exception("Download failed")
        mock_article_class.return_value = mock_article
        
        # Setup BeautifulSoup mock
        mock_response = Mock()
        mock_response.content = b"""
        <html>
            <body>
                <article>
                    <p>This is paragraph one with good content.</p>
                    <p>This is paragraph two with more content.</p>
                    <p>This is paragraph three with even more content.</p>
                </article>
            </body>
        </html>
        """
        mock_response.raise_for_status = Mock()
        mock_requests_get.return_value = mock_response
        
        scraper = ArticleScraper()
        result = scraper.scrape("https://example.com/article")
        
        # Verify
        assert result.success is True
        assert len(result.full_text) > 100
        assert "paragraph one" in result.full_text.lower()
        assert result.published_date is None  # BeautifulSoup doesn't extract dates
    
    @patch('src.article_scraper.requests.get')
    @patch('src.article_scraper.Article')
    def test_scrape_handles_404_error(self, mock_article_class, mock_requests_get):
        """Test handling of 404 errors."""
        # Make newspaper3k fail
        mock_article = Mock()
        mock_article.download.side_effect = Exception("Download failed")
        mock_article_class.return_value = mock_article
        
        # Make requests return 404
        mock_response = Mock()
        mock_response.status_code = 404
        mock_response.raise_for_status.side_effect = Exception("404 Not Found")
        mock_requests_get.return_value = mock_response
        
        scraper = ArticleScraper()
        result = scraper.scrape("https://example.com/nonexistent")
        
        # Verify
        assert result.success is False
        assert result.error_message is not None
        assert "404" in result.error_message or "error" in result.error_message.lower()
    
    @patch('src.article_scraper.requests.get')
    @patch('src.article_scraper.Article')
    def test_scrape_handles_timeout(self, mock_article_class, mock_requests_get):
        """Test handling of request timeouts."""
        # Make newspaper3k fail
        mock_article = Mock()
        mock_article.download.side_effect = Exception("Download failed")
        mock_article_class.return_value = mock_article
        
        # Make requests timeout
        from requests.exceptions import Timeout
        mock_requests_get.side_effect = Timeout("Request timed out")
        
        scraper = ArticleScraper(timeout=5)
        result = scraper.scrape("https://example.com/slow")
        
        # Verify
        assert result.success is False
        assert result.error_message is not None
        assert "timeout" in result.error_message.lower()
    
    @patch('src.article_scraper.Article')
    def test_scrape_handles_insufficient_content(self, mock_article_class):
        """Test handling when extracted content is too short."""
        # Setup mock with very short content
        mock_article = Mock()
        mock_article.text = "Short"
        mock_article.publish_date = None
        mock_article_class.return_value = mock_article
        
        # Mock the fallback to also fail
        with patch('src.article_scraper.requests.get') as mock_requests:
            mock_response = Mock()
            mock_response.content = b"<html><body><p>Short</p></body></html>"
            mock_response.raise_for_status = Mock()
            mock_requests.return_value = mock_response
            
            scraper = ArticleScraper()
            result = scraper.scrape("https://example.com/short")
            
            # Verify - should fail due to insufficient content
            assert result.success is False
    
    @patch('src.article_scraper.requests.get')
    @patch('src.article_scraper.Article')
    def test_scrape_removes_script_and_style_tags(self, mock_article_class, mock_requests_get):
        """Test that script and style tags are removed during scraping."""
        # Make newspaper3k fail
        mock_article = Mock()
        mock_article.download.side_effect = Exception("Download failed")
        mock_article_class.return_value = mock_article
        
        # Setup HTML with script and style tags
        mock_response = Mock()
        mock_response.content = b"""
        <html>
            <body>
                <script>alert('test');</script>
                <style>.test { color: red; }</style>
                <article>
                    <p>This is the actual article content that should be extracted.</p>
                    <p>This is more content that should be included in the result.</p>
                </article>
            </body>
        </html>
        """
        mock_response.raise_for_status = Mock()
        mock_requests_get.return_value = mock_response
        
        scraper = ArticleScraper()
        result = scraper.scrape("https://example.com/article")
        
        # Verify
        assert result.success is True
        assert "alert" not in result.full_text
        assert "color: red" not in result.full_text
        assert "actual article content" in result.full_text
    
    def test_scraped_content_dataclass(self):
        """Test ScrapedContent dataclass structure."""
        timestamp = datetime.now()
        content = ScrapedContent(
            full_text="Test content",
            published_date=datetime(2024, 1, 15),
            scrape_timestamp=timestamp,
            success=True,
            error_message=None
        )
        
        assert content.full_text == "Test content"
        assert content.published_date == datetime(2024, 1, 15)
        assert content.scrape_timestamp == timestamp
        assert content.success is True
        assert content.error_message is None
    
    @patch('src.article_scraper.requests.get')
    @patch('src.article_scraper.Article')
    def test_scrape_handles_403_forbidden(self, mock_article_class, mock_requests_get):
        """Test handling of 403 Forbidden errors (paywalls, access denied)."""
        # Make newspaper3k fail
        mock_article = Mock()
        mock_article.download.side_effect = Exception("Download failed")
        mock_article_class.return_value = mock_article
        
        # Make requests return 403
        from requests.exceptions import HTTPError
        mock_response = Mock()
        mock_response.status_code = 403
        mock_response.raise_for_status.side_effect = HTTPError("403 Forbidden")
        mock_requests_get.return_value = mock_response
        
        scraper = ArticleScraper()
        result = scraper.scrape("https://example.com/paywall")
        
        # Verify - should fail gracefully without crashing
        assert result.success is False
        assert result.error_message is not None
        assert "403" in result.error_message or "error" in result.error_message.lower()
        assert result.full_text == ""
    
    @patch('src.article_scraper.requests.get')
    @patch('src.article_scraper.Article')
    def test_scrape_handles_network_error(self, mock_article_class, mock_requests_get):
        """Test handling of network connection errors."""
        # Make newspaper3k fail
        mock_article = Mock()
        mock_article.download.side_effect = Exception("Download failed")
        mock_article_class.return_value = mock_article
        
        # Make requests fail with connection error
        from requests.exceptions import ConnectionError
        mock_requests_get.side_effect = ConnectionError("Network unreachable")
        
        scraper = ArticleScraper()
        result = scraper.scrape("https://example.com/unreachable")
        
        # Verify - should fail gracefully without crashing
        assert result.success is False
        assert result.error_message is not None
        assert "error" in result.error_message.lower()
    
    @patch('src.article_scraper.requests.get')
    @patch('src.article_scraper.Article')
    def test_scrape_continues_after_failure(self, mock_article_class, mock_requests_get):
        """Test that scraper can continue processing after a failure."""
        # Make newspaper3k fail
        mock_article = Mock()
        mock_article.download.side_effect = Exception("Download failed")
        mock_article_class.return_value = mock_article
        
        # First request fails
        from requests.exceptions import Timeout
        mock_requests_get.side_effect = Timeout("Request timed out")
        
        scraper = ArticleScraper()
        
        # First scrape fails
        result1 = scraper.scrape("https://example.com/timeout")
        assert result1.success is False
        
        # Setup second request to succeed
        mock_requests_get.side_effect = None
        mock_response = Mock()
        mock_response.content = b"""
        <html>
            <body>
                <article>
                    <p>This is a successful article after a previous failure.</p>
                    <p>The scraper should continue working normally.</p>
                </article>
            </body>
        </html>
        """
        mock_response.raise_for_status = Mock()
        mock_requests_get.return_value = mock_response
        
        # Second scrape succeeds
        result2 = scraper.scrape("https://example.com/success")
        assert result2.success is True
        assert "successful article" in result2.full_text.lower()
