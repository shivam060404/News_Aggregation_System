"""Unit tests for the PipelineOrchestrator component."""
import pytest
from datetime import datetime
from unittest.mock import Mock, MagicMock
from src.pipeline_orchestrator import PipelineOrchestrator, PipelineResult, PipelineError
from src.config import Config, TestSet, StorageType
from src.news_collector import RawArticle
from src.article_scraper import ScrapedContent
from src.ai_summarizer import Summary
from src.storage_layer import ProcessedArticle


@pytest.fixture
def test_set():
    """Create a test set for testing."""
    return TestSet(
        name="Test Set",
        entities=["Microsoft", "Google", "Apple"]
    )


@pytest.fixture
def config():
    """Create a test configuration."""
    return Config(
        news_api_key="test_key",
        ai_api_key="test_ai_key",
        ai_provider="openai",
        storage_type=StorageType.CSV,
        output_path="test_output.csv"
    )


@pytest.fixture
def mock_components():
    """Create mock components for testing."""
    collector = Mock()
    classifier = Mock()
    scraper = Mock()
    summarizer = Mock()
    storage = Mock()
    
    return {
        "collector": collector,
        "classifier": classifier,
        "scraper": scraper,
        "summarizer": summarizer,
        "storage": storage
    }


def test_pipeline_orchestrator_initialization(config, test_set, mock_components):
    """Test that PipelineOrchestrator initializes correctly."""
    orchestrator = PipelineOrchestrator(
        config=config,
        test_set=test_set,
        collector=mock_components["collector"],
        classifier=mock_components["classifier"],
        scraper=mock_components["scraper"],
        summarizer=mock_components["summarizer"],
        storage=mock_components["storage"]
    )
    
    assert orchestrator.config == config
    assert orchestrator.test_set == test_set
    assert orchestrator.total_collected == 0
    assert orchestrator.total_classified == 0
    assert orchestrator.total_scraped == 0
    assert orchestrator.total_summarized == 0
    assert orchestrator.total_stored == 0
    assert orchestrator.errors == []


def test_pipeline_run_with_no_articles(config, test_set, mock_components):
    """Test pipeline execution when no articles are collected."""
    mock_components["collector"].fetch_news.return_value = []
    
    orchestrator = PipelineOrchestrator(
        config=config,
        test_set=test_set,
        **mock_components
    )
    
    result = orchestrator.run()
    
    assert result.total_collected == 0
    assert result.total_classified == 0
    assert result.total_scraped == 0
    assert result.total_summarized == 0
    assert result.total_stored == 0
    assert len(result.errors) == 0


def test_pipeline_run_with_successful_article(config, test_set, mock_components):
    """Test pipeline execution with a successful article processing."""
    # Setup mock data
    raw_article = RawArticle(
        title="Microsoft announces new AI features",
        url="https://example.com/article1",
        published_date=datetime.now(),
        source="Test Source",
        snippet="Microsoft unveils new AI capabilities"
    )
    
    scraped_content = ScrapedContent(
        full_text="Microsoft has announced new AI features for its products...",
        published_date=datetime.now(),
        scrape_timestamp=datetime.now(),
        success=True,
        error_message=None
    )
    
    summary = Summary(
        text="Microsoft announces new AI features for its products.",
        word_count=35,
        success=True,
        error_message=None
    )
    
    # Configure mocks
    mock_components["collector"].fetch_news.return_value = [raw_article]
    mock_components["scraper"].scrape.return_value = scraped_content
    mock_components["classifier"].classify.return_value = ["Microsoft"]
    mock_components["summarizer"].summarize.return_value = summary
    mock_components["storage"].save_article.return_value = True
    
    orchestrator = PipelineOrchestrator(
        config=config,
        test_set=test_set,
        **mock_components
    )
    
    result = orchestrator.run()
    
    assert result.total_collected == 1
    assert result.total_scraped == 1
    assert result.total_classified == 1
    assert result.total_summarized == 1
    assert result.total_stored == 1
    assert len(result.errors) == 0


def test_pipeline_skips_article_with_no_entities(config, test_set, mock_components):
    """Test that pipeline skips articles with no matching entities."""
    raw_article = RawArticle(
        title="Unrelated news article",
        url="https://example.com/article1",
        published_date=datetime.now(),
        source="Test Source",
        snippet="Some unrelated content"
    )
    
    scraped_content = ScrapedContent(
        full_text="This article doesn't mention any of our entities...",
        published_date=datetime.now(),
        scrape_timestamp=datetime.now(),
        success=True,
        error_message=None
    )
    
    # Configure mocks
    mock_components["collector"].fetch_news.return_value = [raw_article]
    mock_components["scraper"].scrape.return_value = scraped_content
    mock_components["classifier"].classify.return_value = []  # No entities
    
    orchestrator = PipelineOrchestrator(
        config=config,
        test_set=test_set,
        **mock_components
    )
    
    result = orchestrator.run()
    
    assert result.total_collected == 1
    assert result.total_scraped == 1
    assert result.total_classified == 0  # Not classified
    assert result.total_summarized == 0  # Not summarized
    assert result.total_stored == 0  # Not stored
    assert len(result.errors) == 0  # No entities is not an error


def test_pipeline_continues_on_scraping_failure(config, test_set, mock_components):
    """Test that pipeline continues processing when scraping fails."""
    raw_article1 = RawArticle(
        title="Article 1",
        url="https://example.com/article1",
        published_date=datetime.now(),
        source="Test Source",
        snippet="Content 1"
    )
    
    raw_article2 = RawArticle(
        title="Article 2",
        url="https://example.com/article2",
        published_date=datetime.now(),
        source="Test Source",
        snippet="Content 2"
    )
    
    failed_scrape = ScrapedContent(
        full_text="",
        published_date=None,
        scrape_timestamp=datetime.now(),
        success=False,
        error_message="HTTP error 404"
    )
    
    successful_scrape = ScrapedContent(
        full_text="Google announces new product...",
        published_date=datetime.now(),
        scrape_timestamp=datetime.now(),
        success=True,
        error_message=None
    )
    
    summary = Summary(
        text="Google announces new product with innovative features.",
        word_count=35,
        success=True,
        error_message=None
    )
    
    # Configure mocks
    mock_components["collector"].fetch_news.return_value = [raw_article1, raw_article2]
    mock_components["scraper"].scrape.side_effect = [failed_scrape, successful_scrape]
    mock_components["classifier"].classify.return_value = ["Google"]
    mock_components["summarizer"].summarize.return_value = summary
    mock_components["storage"].save_article.return_value = True
    
    orchestrator = PipelineOrchestrator(
        config=config,
        test_set=test_set,
        **mock_components
    )
    
    result = orchestrator.run()
    
    assert result.total_collected == 2
    assert result.total_scraped == 1  # Only one successful scrape
    assert result.total_classified == 1
    assert result.total_summarized == 1
    assert result.total_stored == 1
    assert len(result.errors) == 1
    assert result.errors[0].stage == "scraping"


def test_pipeline_continues_on_summarization_failure(config, test_set, mock_components):
    """Test that pipeline continues processing when summarization fails."""
    raw_article = RawArticle(
        title="Test article",
        url="https://example.com/article1",
        published_date=datetime.now(),
        source="Test Source",
        snippet="Test content"
    )
    
    scraped_content = ScrapedContent(
        full_text="Apple releases new iPhone model...",
        published_date=datetime.now(),
        scrape_timestamp=datetime.now(),
        success=True,
        error_message=None
    )
    
    failed_summary = Summary(
        text="",
        word_count=0,
        success=False,
        error_message="AI API rate limit exceeded"
    )
    
    # Configure mocks
    mock_components["collector"].fetch_news.return_value = [raw_article]
    mock_components["scraper"].scrape.return_value = scraped_content
    mock_components["classifier"].classify.return_value = ["Apple"]
    mock_components["summarizer"].summarize.return_value = failed_summary
    
    orchestrator = PipelineOrchestrator(
        config=config,
        test_set=test_set,
        **mock_components
    )
    
    result = orchestrator.run()
    
    assert result.total_collected == 1
    assert result.total_scraped == 1
    assert result.total_classified == 1
    assert result.total_summarized == 0  # Summarization failed
    assert result.total_stored == 0  # Not stored due to failed summarization
    assert len(result.errors) == 1
    assert result.errors[0].stage == "summarization"


def test_pipeline_tracks_storage_errors(config, test_set, mock_components):
    """Test that pipeline tracks storage errors."""
    raw_article = RawArticle(
        title="Test article",
        url="https://example.com/article1",
        published_date=datetime.now(),
        source="Test Source",
        snippet="Test content"
    )
    
    scraped_content = ScrapedContent(
        full_text="Microsoft launches new service...",
        published_date=datetime.now(),
        scrape_timestamp=datetime.now(),
        success=True,
        error_message=None
    )
    
    summary = Summary(
        text="Microsoft launches new cloud service for enterprises.",
        word_count=35,
        success=True,
        error_message=None
    )
    
    # Configure mocks
    mock_components["collector"].fetch_news.return_value = [raw_article]
    mock_components["scraper"].scrape.return_value = scraped_content
    mock_components["classifier"].classify.return_value = ["Microsoft"]
    mock_components["summarizer"].summarize.return_value = summary
    mock_components["storage"].save_article.return_value = False  # Storage fails
    
    orchestrator = PipelineOrchestrator(
        config=config,
        test_set=test_set,
        **mock_components
    )
    
    result = orchestrator.run()
    
    assert result.total_collected == 1
    assert result.total_scraped == 1
    assert result.total_classified == 1
    assert result.total_summarized == 1
    assert result.total_stored == 0  # Storage failed
    assert len(result.errors) == 1
    assert result.errors[0].stage == "storage"


def test_pipeline_processes_multiple_articles(config, test_set, mock_components):
    """Test pipeline processing multiple articles with mixed results."""
    articles = [
        RawArticle(
            title=f"Article {i}",
            url=f"https://example.com/article{i}",
            published_date=datetime.now(),
            source="Test Source",
            snippet=f"Content {i}"
        )
        for i in range(5)
    ]
    
    scraped_content = ScrapedContent(
        full_text="Test content with Microsoft and Google...",
        published_date=datetime.now(),
        scrape_timestamp=datetime.now(),
        success=True,
        error_message=None
    )
    
    summary = Summary(
        text="Test summary of the article content.",
        word_count=35,
        success=True,
        error_message=None
    )
    
    # Configure mocks
    mock_components["collector"].fetch_news.return_value = articles
    mock_components["scraper"].scrape.return_value = scraped_content
    mock_components["classifier"].classify.return_value = ["Microsoft", "Google"]
    mock_components["summarizer"].summarize.return_value = summary
    mock_components["storage"].save_article.return_value = True
    
    orchestrator = PipelineOrchestrator(
        config=config,
        test_set=test_set,
        **mock_components
    )
    
    result = orchestrator.run()
    
    assert result.total_collected == 5
    assert result.total_scraped == 5
    assert result.total_classified == 5
    assert result.total_summarized == 5
    assert result.total_stored == 5
    assert len(result.errors) == 0
