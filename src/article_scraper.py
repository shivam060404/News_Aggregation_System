"""Article scraping component for extracting full content from URLs."""
import logging
from dataclasses import dataclass
from datetime import datetime
from typing import Optional
import requests
from newspaper import Article
from bs4 import BeautifulSoup


logger = logging.getLogger(__name__)


@dataclass
class ScrapedContent:
    """Result of article scraping operation."""
    full_text: str
    published_date: Optional[datetime]
    scrape_timestamp: datetime
    success: bool
    error_message: Optional[str]


class ArticleScraper:
    """Scrapes full article content from URLs."""
    
    def __init__(self, timeout: int = 30):
        """Initialize the ArticleScraper.
        
        Args:
            timeout: Request timeout in seconds (default: 30)
        """
        self.timeout = timeout
    
    def scrape(self, url: str) -> ScrapedContent:
        """Extract full article content from a URL.
        
        Attempts to extract article content using newspaper3k first,
        then falls back to BeautifulSoup if that fails.
        
        Args:
            url: Article URL to scrape
            
        Returns:
            ScrapedContent with extracted data and success status
        """
        scrape_timestamp = datetime.now()
        
        # Try newspaper3k first (better for news articles)
        try:
            article = Article(url)
            article.download()
            article.parse()
            
            # Extract text
            full_text = article.text.strip()
            
            # Extract published date if available
            published_date = None
            if article.publish_date:
                published_date = article.publish_date
            
            # Validate we got meaningful content
            if full_text and len(full_text) > 100:
                logger.info(f"Successfully scraped article from {url} using newspaper3k")
                return ScrapedContent(
                    full_text=full_text,
                    published_date=published_date,
                    scrape_timestamp=scrape_timestamp,
                    success=True,
                    error_message=None
                )
            else:
                # Content too short, try fallback
                logger.warning(f"newspaper3k extracted insufficient content from {url}, trying fallback")
                return self._scrape_with_beautifulsoup(url, scrape_timestamp)
        
        except Exception as e:
            logger.warning(f"newspaper3k failed for {url}: {e}, trying fallback")
            return self._scrape_with_beautifulsoup(url, scrape_timestamp)
    
    def _scrape_with_beautifulsoup(self, url: str, scrape_timestamp: datetime) -> ScrapedContent:
        """Fallback scraping method using BeautifulSoup.
        
        Args:
            url: Article URL to scrape
            scrape_timestamp: Timestamp when scraping started
            
        Returns:
            ScrapedContent with extracted data and success status
        """
        try:
            # Fetch the page
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
            }
            response = requests.get(url, headers=headers, timeout=self.timeout)
            response.raise_for_status()
            
            # Parse with BeautifulSoup
            soup = BeautifulSoup(response.content, 'lxml')
            
            # Remove script and style elements
            for element in soup(['script', 'style', 'nav', 'header', 'footer', 'aside']):
                element.decompose()
            
            # Try to find article content
            # Look for common article containers
            article_content = None
            for selector in ['article', 'div.article-content', 'div.post-content', 'div.entry-content']:
                article_content = soup.select_one(selector)
                if article_content:
                    break
            
            # If no article container found, use body
            if not article_content:
                article_content = soup.find('body')
            
            if article_content:
                # Extract text from paragraphs
                paragraphs = article_content.find_all('p')
                full_text = '\n\n'.join(p.get_text().strip() for p in paragraphs if p.get_text().strip())
                
                if full_text and len(full_text) > 100:
                    logger.info(f"Successfully scraped article from {url} using BeautifulSoup")
                    return ScrapedContent(
                        full_text=full_text,
                        published_date=None,  # BeautifulSoup doesn't extract dates reliably
                        scrape_timestamp=scrape_timestamp,
                        success=True,
                        error_message=None
                    )
            
            # If we got here, extraction failed
            error_msg = "Could not extract sufficient content from page"
            logger.error(f"Failed to scrape {url}: {error_msg}")
            return ScrapedContent(
                full_text="",
                published_date=None,
                scrape_timestamp=scrape_timestamp,
                success=False,
                error_message=error_msg
            )
        
        except requests.exceptions.HTTPError as e:
            # Try to get status code from response if available
            status_code = getattr(e.response, 'status_code', 'unknown') if hasattr(e, 'response') and e.response else 'unknown'
            error_msg = f"HTTP error {status_code}: {e}"
            logger.error(f"Failed to scrape {url}: {error_msg}")
            return ScrapedContent(
                full_text="",
                published_date=None,
                scrape_timestamp=scrape_timestamp,
                success=False,
                error_message=error_msg
            )
        
        except requests.exceptions.Timeout:
            error_msg = f"Request timeout after {self.timeout} seconds"
            logger.error(f"Failed to scrape {url}: {error_msg}")
            return ScrapedContent(
                full_text="",
                published_date=None,
                scrape_timestamp=scrape_timestamp,
                success=False,
                error_message=error_msg
            )
        
        except requests.exceptions.RequestException as e:
            error_msg = f"Request error: {e}"
            logger.error(f"Failed to scrape {url}: {error_msg}")
            return ScrapedContent(
                full_text="",
                published_date=None,
                scrape_timestamp=scrape_timestamp,
                success=False,
                error_message=error_msg
            )
        
        except Exception as e:
            error_msg = f"Unexpected error: {e}"
            logger.error(f"Failed to scrape {url}: {error_msg}")
            return ScrapedContent(
                full_text="",
                published_date=None,
                scrape_timestamp=scrape_timestamp,
                success=False,
                error_message=error_msg
            )
