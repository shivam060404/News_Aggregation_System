"""Pipeline orchestrator for coordinating the news aggregation workflow."""
import logging
from dataclasses import dataclass
from datetime import datetime
from typing import List, Optional
from src.config import Config, TestSet
from src.news_collector import NewsCollector, RawArticle
from src.entity_classifier import EntityClassifier
from src.article_scraper import ArticleScraper, ScrapedContent
from src.ai_summarizer import AISummarizer, Summary
from src.storage_layer import StorageLayer, ProcessedArticle


logger = logging.getLogger(__name__)


@dataclass
class PipelineError:
    """Error that occurred during pipeline processing."""
    stage: str
    article_url: str
    error_message: str
    timestamp: datetime


@dataclass
class PipelineResult:
    """Result of pipeline execution with statistics."""
    total_collected: int
    total_classified: int
    total_scraped: int
    total_summarized: int
    total_stored: int
    errors: List[PipelineError]


class PipelineOrchestrator:
    """Orchestrates the complete news aggregation pipeline."""
    
    def __init__(
        self,
        config: Config,
        test_set: TestSet,
        collector: NewsCollector,
        classifier: EntityClassifier,
        scraper: ArticleScraper,
        summarizer: AISummarizer,
        storage: StorageLayer
    ):
        """Initialize the PipelineOrchestrator.
        
        Args:
            config: System configuration
            test_set: Selected test set of entities
            collector: NewsCollector instance
            classifier: EntityClassifier instance
            scraper: ArticleScraper instance
            summarizer: AISummarizer instance
            storage: StorageLayer instance
        """
        self.config = config
        self.test_set = test_set
        self.collector = collector
        self.classifier = classifier
        self.scraper = scraper
        self.summarizer = summarizer
        self.storage = storage
        
        # Statistics tracking
        self.total_collected = 0
        self.total_classified = 0
        self.total_scraped = 0
        self.total_summarized = 0
        self.total_stored = 0
        self.errors: List[PipelineError] = []
    
    def run(self) -> PipelineResult:
        """Execute the complete pipeline from collection to storage.
        
        Returns:
            PipelineResult with execution statistics and errors
        """
        logger.info("=" * 60)
        logger.info("Starting News Aggregation Pipeline")
        logger.info(f"Test Set: {self.test_set.name}")
        logger.info(f"Entities: {', '.join(self.test_set.entities)}")
        logger.info("=" * 60)
        
        # Stage 1: Collect news
        logger.info("\n[Stage 1/4] Collecting news articles...")
        raw_articles = self.collector.fetch_news(self.test_set.entities)
        self.total_collected = len(raw_articles)
        logger.info(f"Collected {self.total_collected} articles")
        
        if self.total_collected == 0:
            logger.warning("No articles collected. Pipeline complete.")
            return self._build_result()
        
        # Stage 2-5: Process each article
        logger.info(f"\n[Stage 2-4] Processing {self.total_collected} articles...")
        
        for i, raw_article in enumerate(raw_articles, 1):
            logger.info(f"\nProcessing article {i}/{self.total_collected}: {raw_article.title[:60]}...")
            
            processed_article = self._process_article(raw_article)
            
            if processed_article:
                # Save to storage
                success = self.storage.save_article(processed_article)
                if success:
                    self.total_stored += 1
                    logger.info(f"✓ Article stored successfully")
                else:
                    self._log_error("storage", raw_article.url, "Failed to save article to storage")
            else:
                logger.info(f"✗ Article skipped (no matching entities or processing failed)")
        
        # Log final results
        logger.info("\n" + "=" * 60)
        logger.info("Pipeline Execution Complete")
        logger.info("=" * 60)
        
        return self._build_result()
    
    def _process_article(self, raw_article: RawArticle) -> Optional[ProcessedArticle]:
        """Process a single article through all pipeline stages.
        
        Args:
            raw_article: RawArticle to process
            
        Returns:
            ProcessedArticle if successful, None if article should be skipped
        """
        # Stage 2: Scrape content
        scraped = self.scraper.scrape(raw_article.url)
        
        if not scraped.success:
            self._log_error("scraping", raw_article.url, scraped.error_message or "Unknown scraping error")
            return None
        
        self.total_scraped += 1
        
        # Stage 3: Classify entities
        entities = self.classifier.classify(raw_article, scraped.full_text)
        
        if not entities:
            # No matching entities - skip this article (expected behavior, not an error)
            logger.debug(f"Article has no matching entities, skipping: {raw_article.url}")
            return None
        
        self.total_classified += 1
        logger.debug(f"Article classified with entities: {', '.join(entities)}")
        
        # Stage 4: Generate summary
        summary = self.summarizer.summarize(scraped.full_text)
        
        if not summary.success:
            self._log_error("summarization", raw_article.url, summary.error_message or "Unknown summarization error")
            return None
        
        self.total_summarized += 1
        
        # Stage 5: Build ProcessedArticle
        processed_article = ProcessedArticle(
            title=raw_article.title,
            url=raw_article.url,
            published_date=scraped.published_date or scraped.scrape_timestamp,
            entity_tags=entities,
            summary=summary.text,
            source=raw_article.source,
            created_at=datetime.now()
        )
        
        return processed_article
    
    def _log_error(self, stage: str, article_url: str, error_message: str):
        """Log an error that occurred during pipeline processing.
        
        Args:
            stage: Pipeline stage where error occurred
            article_url: URL of the article being processed
            error_message: Description of the error
        """
        error = PipelineError(
            stage=stage,
            article_url=article_url,
            error_message=error_message,
            timestamp=datetime.now()
        )
        self.errors.append(error)
        logger.error(f"[{stage.upper()}] Error processing {article_url}: {error_message}")
    
    def _build_result(self) -> PipelineResult:
        """Build the final pipeline result with statistics.
        
        Returns:
            PipelineResult with execution statistics
        """
        result = PipelineResult(
            total_collected=self.total_collected,
            total_classified=self.total_classified,
            total_scraped=self.total_scraped,
            total_summarized=self.total_summarized,
            total_stored=self.total_stored,
            errors=self.errors
        )
        
        # Log statistics
        logger.info(f"Total Collected:   {result.total_collected}")
        logger.info(f"Total Scraped:     {result.total_scraped}")
        logger.info(f"Total Classified:  {result.total_classified}")
        logger.info(f"Total Summarized:  {result.total_summarized}")
        logger.info(f"Total Stored:      {result.total_stored}")
        logger.info(f"Total Errors:      {len(result.errors)}")
        
        if result.errors:
            logger.info("\nErrors by stage:")
            error_counts = {}
            for error in result.errors:
                error_counts[error.stage] = error_counts.get(error.stage, 0) + 1
            for stage, count in error_counts.items():
                logger.info(f"  {stage}: {count}")
        
        return result
