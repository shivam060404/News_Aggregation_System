"""Unit tests for NewsCollector component."""
import pytest
from datetime import datetime, timedelta
from unittest.mock import Mock, patch
from src.news_collector import NewsCollector, RawArticle


class TestNewsCollector:
    """Tests for NewsCollector class."""
    
    def test_build_query_single_entity(self):
        """Test query construction with single entity."""
        collector = NewsCollector(api_key="test_key")
        query = collector._build_query(["Microsoft"])
        assert query == '"Microsoft"'
    
    def test_build_query_multiple_entities(self):
        """Test query construction with multiple entities."""
        collector = NewsCollector(api_key="test_key")
        query = collector._build_query(["Microsoft", "Google", "Apple"])
        assert query == '"Microsoft" OR "Google" OR "Apple"'
    
    def test_parse_response_valid_articles(self):
        """Test parsing valid API response."""
        collector = NewsCollector(api_key="test_key")
        
        response = {
            "status": "ok",
            "articles": [
                {
                    "title": "Test Article 1",
                    "url": "https://example.com/article1",
                    "publishedAt": "2024-01-15T10:30:00Z",
                    "source": {"name": "Test Source"},
                    "description": "Test description"
                },
                {
                    "title": "Test Article 2",
                    "url": "https://example.com/article2",
                    "publishedAt": "2024-01-16T14:20:00Z",
                    "source": {"name": "Another Source"},
                    "description": "Another description"
                }
            ]
        }
        
        articles = collector._parse_response(response)
        
        assert len(articles) == 2
        assert articles[0].title == "Test Article 1"
        assert articles[0].url == "https://example.com/article1"
        assert articles[0].source == "Test Source"
        assert articles[1].title == "Test Article 2"
    
    def test_parse_response_missing_fields(self):
        """Test parsing response with missing fields."""
        collector = NewsCollector(api_key="test_key")
        
        response = {
            "status": "ok",
            "articles": [
                {
                    "title": "Valid Article",
                    "url": "https://example.com/valid",
                    "source": {"name": "Test Source"}
                },
                {
                    # Missing title - should be skipped
                    "url": "https://example.com/no-title",
                    "source": {"name": "Test Source"}
                },
                {
                    "title": "No URL Article",
                    # Missing URL - should be skipped
                    "source": {"name": "Test Source"}
                }
            ]
        }
        
        articles = collector._parse_response(response)
        
        # Only the valid article should be included
        assert len(articles) == 1
        assert articles[0].title == "Valid Article"
    
    def test_parse_response_invalid_date(self):
        """Test parsing response with invalid date format."""
        collector = NewsCollector(api_key="test_key")
        
        response = {
            "status": "ok",
            "articles": [
                {
                    "title": "Article with bad date",
                    "url": "https://example.com/article",
                    "publishedAt": "invalid-date-format",
                    "source": {"name": "Test Source"}
                }
            ]
        }
        
        articles = collector._parse_response(response)
        
        assert len(articles) == 1
        assert articles[0].published_date is None  # Should handle gracefully
    
    @patch('src.news_collector.requests.get')
    def test_fetch_news_success(self, mock_get):
        """Test successful news fetching."""
        collector = NewsCollector(api_key="test_key")
        
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "status": "ok",
            "articles": [
                {
                    "title": "Test Article",
                    "url": "https://example.com/article",
                    "publishedAt": "2024-01-15T10:30:00Z",
                    "source": {"name": "Test Source"},
                    "description": "Test description"
                }
            ]
        }
        mock_get.return_value = mock_response
        
        articles = collector.fetch_news(["Microsoft", "Google"])
        
        assert len(articles) == 1
        assert articles[0].title == "Test Article"
        assert mock_get.called
    
    @patch('src.news_collector.requests.get')
    def test_fetch_news_api_error(self, mock_get):
        """Test handling of API error response."""
        collector = NewsCollector(api_key="test_key")
        
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "status": "error",
            "message": "API key invalid"
        }
        mock_get.return_value = mock_response
        
        articles = collector.fetch_news(["Microsoft"])
        
        assert len(articles) == 0
    
    @patch('src.news_collector.requests.get')
    def test_fetch_news_network_error(self, mock_get):
        """Test handling of network errors."""
        collector = NewsCollector(api_key="test_key", max_retries=2)
        
        mock_get.side_effect = Exception("Network error")
        
        articles = collector.fetch_news(["Microsoft"])
        
        assert len(articles) == 0
    
    @patch('src.news_collector.requests.get')
    @patch('src.news_collector.time.sleep')
    def test_fetch_news_rate_limit_retry(self, mock_sleep, mock_get):
        """Test exponential backoff on rate limit errors."""
        collector = NewsCollector(api_key="test_key", max_retries=3)
        
        # First two calls return 429, third succeeds
        mock_response_429 = Mock()
        mock_response_429.status_code = 429
        
        mock_response_success = Mock()
        mock_response_success.status_code = 200
        mock_response_success.json.return_value = {
            "status": "ok",
            "articles": [
                {
                    "title": "Test Article",
                    "url": "https://example.com/article",
                    "source": {"name": "Test Source"}
                }
            ]
        }
        
        mock_get.side_effect = [mock_response_429, mock_response_429, mock_response_success]
        
        articles = collector.fetch_news(["Microsoft"])
        
        assert len(articles) == 1
        assert mock_sleep.call_count == 2  # Should sleep twice before success
    
    @patch('src.news_collector.requests.get')
    def test_fetch_news_pagination(self, mock_get):
        """Test pagination handling."""
        collector = NewsCollector(api_key="test_key")
        
        # First page with 100 articles
        mock_response_page1 = Mock()
        mock_response_page1.status_code = 200
        mock_response_page1.json.return_value = {
            "status": "ok",
            "articles": [
                {
                    "title": f"Article {i}",
                    "url": f"https://example.com/article{i}",
                    "source": {"name": "Test Source"}
                }
                for i in range(100)
            ]
        }
        
        # Second page with 50 articles (less than pageSize, so stop)
        mock_response_page2 = Mock()
        mock_response_page2.status_code = 200
        mock_response_page2.json.return_value = {
            "status": "ok",
            "articles": [
                {
                    "title": f"Article {i}",
                    "url": f"https://example.com/article{i}",
                    "source": {"name": "Test Source"}
                }
                for i in range(100, 150)
            ]
        }
        
        mock_get.side_effect = [mock_response_page1, mock_response_page2]
        
        articles = collector.fetch_news(["Microsoft"])
        
        assert len(articles) == 150
        assert mock_get.call_count == 2
