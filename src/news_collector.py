"""News collection component for fetching articles from external APIs."""
import logging
import time
from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import List, Optional
import requests


logger = logging.getLogger(__name__)


# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)


@dataclass
class RawArticle:
    """Initial article data from news API."""
    title: str
    url: str
    published_date: Optional[datetime]
    source: str
    snippet: Optional[str]


class NewsCollector:
    """Collects news articles from external news APIs."""
    
    def __init__(self, api_key: str, max_retries: int = 3):
        """Initialize the NewsCollector.
        
        Args:
            api_key: API key for the news service
            max_retries: Maximum number of retry attempts for failed requests
        """
        self.api_key = api_key
        self.base_url = "https://newsapi.org/v2/everything"
        self.max_retries = max_retries
    
    def fetch_news(self, entities: List[str], days_back: int = 7) -> List[RawArticle]:
        """Fetch news articles for the given entities within the specified time window.
        
        Args:
            entities: List of company/entity names to search for
            days_back: Number of days to look back (default: 7)
            
        Returns:
            List of RawArticle instances
        """
        query = self._build_query(entities)
        from_date = datetime.now() - timedelta(days=days_back)
        
        params = {
            "q": query,
            "from": from_date.strftime("%Y-%m-%d"),
            "sortBy": "publishedAt",
            "language": "en",
            "pageSize": 100,  # Maximum results per page
            "apiKey": self.api_key
        }
        
        all_articles = []
        page = 1
        
        # Handle pagination - fetch up to 3 pages
        while page <= 3:
            params["page"] = page
            
            articles = self._fetch_with_retry(params)
            if not articles:
                break
            
            all_articles.extend(articles)
            
            # If we got fewer than pageSize results, we've reached the end
            if len(articles) < params["pageSize"]:
                break
            
            page += 1
        
        logger.info(f"Fetched {len(all_articles)} articles for entities: {', '.join(entities)}")
        return all_articles
    
    def _fetch_with_retry(self, params: dict) -> List[RawArticle]:
        """Fetch articles with exponential backoff retry logic.
        
        Args:
            params: Request parameters
            
        Returns:
            List of RawArticle instances
        """
        for attempt in range(self.max_retries):
            try:
                response = requests.get(self.base_url, params=params, timeout=30)
                
                # Handle rate limiting (429) with exponential backoff
                if response.status_code == 429:
                    wait_time = 2 ** attempt  # Exponential backoff: 1s, 2s, 4s
                    logger.warning(f"Rate limit hit. Retrying in {wait_time} seconds... (attempt {attempt + 1}/{self.max_retries})")
                    time.sleep(wait_time)
                    continue
                
                response.raise_for_status()
                data = response.json()
                
                if data.get("status") != "ok":
                    error_msg = data.get("message", "Unknown error")
                    logger.error(f"API returned error status: {error_msg}")
                    return []
                
                return self._parse_response(data)
            
            except requests.exceptions.Timeout as e:
                logger.error(f"Request timeout (attempt {attempt + 1}/{self.max_retries}): {e}")
                if attempt < self.max_retries - 1:
                    wait_time = 2 ** attempt
                    time.sleep(wait_time)
                    continue
            
            except requests.exceptions.HTTPError as e:
                logger.error(f"HTTP error: {e}")
                # Don't retry on client errors (4xx except 429)
                if 400 <= response.status_code < 500 and response.status_code != 429:
                    return []
                # Retry on server errors (5xx)
                if attempt < self.max_retries - 1:
                    wait_time = 2 ** attempt
                    time.sleep(wait_time)
                    continue
            
            except requests.exceptions.RequestException as e:
                logger.error(f"Request error (attempt {attempt + 1}/{self.max_retries}): {e}")
                if attempt < self.max_retries - 1:
                    wait_time = 2 ** attempt
                    time.sleep(wait_time)
                    continue
            
            except Exception as e:
                logger.error(f"Unexpected error: {e}")
                return []
        
        logger.error(f"Failed to fetch news after {self.max_retries} attempts")
        return []
    
    def _build_query(self, entities: List[str]) -> str:
        """Build search query from entity list.
        
        Args:
            entities: List of entity names
            
        Returns:
            Query string for the API
        """
        # Use OR operator to search for any of the entities
        return " OR ".join(f'"{entity}"' for entity in entities)
    
    def _parse_response(self, response: dict) -> List[RawArticle]:
        """Parse API response into RawArticle instances.
        
        Args:
            response: JSON response from the API
            
        Returns:
            List of RawArticle instances
        """
        articles = []
        
        for article_data in response.get("articles", []):
            try:
                # Parse published date
                published_at = article_data.get("publishedAt")
                published_date = None
                if published_at:
                    try:
                        published_date = datetime.fromisoformat(published_at.replace("Z", "+00:00"))
                    except (ValueError, AttributeError):
                        logger.warning(f"Could not parse date: {published_at}")
                
                # Create RawArticle instance
                article = RawArticle(
                    title=article_data.get("title", ""),
                    url=article_data.get("url", ""),
                    published_date=published_date,
                    source=article_data.get("source", {}).get("name", "Unknown"),
                    snippet=article_data.get("description")
                )
                
                # Only add articles with valid title and URL
                if article.title and article.url:
                    articles.append(article)
            
            except Exception as e:
                logger.warning(f"Error parsing article: {e}")
                continue
        
        return articles
