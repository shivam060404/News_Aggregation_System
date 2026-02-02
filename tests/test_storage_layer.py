"""Unit tests for storage layer."""
import os
import pytest
import tempfile
from datetime import datetime
from src.storage_layer import (
    StorageLayer,
    ProcessedArticle,
    ArticleFilters,
    DatabaseStorage,
    CSVStorage
)


@pytest.fixture
def sample_article():
    """Create a sample ProcessedArticle for testing."""
    return ProcessedArticle(
        title="Test Article Title",
        url="https://example.com/article1",
        published_date=datetime(2024, 1, 15, 10, 30, 0),
        entity_tags=["Microsoft", "Google"],
        summary="This is a test summary with exactly thirty words to meet the requirement for summaries between thirty and forty words in length for testing purposes.",
        source="Test News",
        created_at=datetime(2024, 1, 15, 11, 0, 0)
    )


@pytest.fixture
def sample_article_2():
    """Create a second sample ProcessedArticle for testing."""
    return ProcessedArticle(
        title="Another Test Article",
        url="https://example.com/article2",
        published_date=datetime(2024, 1, 16, 14, 20, 0),
        entity_tags=["Apple"],
        summary="Another test summary with the required word count for validation purposes and testing the storage layer functionality properly.",
        source="Tech News",
        created_at=datetime(2024, 1, 16, 15, 0, 0)
    )


class TestProcessedArticle:
    """Tests for ProcessedArticle dataclass."""
    
    def test_processed_article_creation(self, sample_article):
        """Test ProcessedArticle can be created with all fields."""
        assert sample_article.title == "Test Article Title"
        assert sample_article.url == "https://example.com/article1"
        assert sample_article.published_date == datetime(2024, 1, 15, 10, 30, 0)
        assert sample_article.entity_tags == ["Microsoft", "Google"]
        assert len(sample_article.summary) > 0
        assert sample_article.source == "Test News"
        assert sample_article.created_at == datetime(2024, 1, 15, 11, 0, 0)


class TestArticleFilters:
    """Tests for ArticleFilters dataclass."""
    
    def test_article_filters_creation(self):
        """Test ArticleFilters can be created with all fields."""
        filters = ArticleFilters(
            entities=["Microsoft", "Google"],
            start_date=datetime(2024, 1, 1),
            end_date=datetime(2024, 1, 31)
        )
        
        assert filters.entities == ["Microsoft", "Google"]
        assert filters.start_date == datetime(2024, 1, 1)
        assert filters.end_date == datetime(2024, 1, 31)
    
    def test_article_filters_optional_fields(self):
        """Test ArticleFilters with optional fields."""
        filters = ArticleFilters()
        
        assert filters.entities is None
        assert filters.start_date is None
        assert filters.end_date is None


class TestDatabaseStorage:
    """Tests for DatabaseStorage class."""
    
    @pytest.fixture
    def db_storage(self):
        """Create a DatabaseStorage instance with SQLite in-memory database."""
        return DatabaseStorage("sqlite:///:memory:")
    
    def test_database_storage_initialization(self, db_storage):
        """Test DatabaseStorage initializes correctly."""
        assert db_storage.database_url == "sqlite:///:memory:"
        assert db_storage.engine is not None
        assert db_storage.Session is not None
    
    def test_save_article_success(self, db_storage, sample_article):
        """Test saving an article to database."""
        result = db_storage.save_article(sample_article)
        
        assert result is True
    
    def test_save_article_duplicate(self, db_storage, sample_article):
        """Test saving duplicate article returns True without error."""
        db_storage.save_article(sample_article)
        result = db_storage.save_article(sample_article)
        
        assert result is True
    
    def test_save_article_missing_title(self, db_storage, sample_article):
        """Test saving article with empty title fails validation."""
        sample_article.title = ""
        result = db_storage.save_article(sample_article)
        
        assert result is False
    
    def test_save_article_missing_url(self, db_storage, sample_article):
        """Test saving article with empty URL fails validation."""
        sample_article.url = ""
        result = db_storage.save_article(sample_article)
        
        assert result is False
    
    def test_save_article_missing_published_date(self, db_storage, sample_article):
        """Test saving article with missing published_date fails validation."""
        sample_article.published_date = None
        result = db_storage.save_article(sample_article)
        
        assert result is False
    
    def test_save_article_empty_entity_tags(self, db_storage, sample_article):
        """Test saving article with empty entity_tags fails validation."""
        sample_article.entity_tags = []
        result = db_storage.save_article(sample_article)
        
        assert result is False
    
    def test_save_article_empty_summary(self, db_storage, sample_article):
        """Test saving article with empty summary fails validation."""
        sample_article.summary = ""
        result = db_storage.save_article(sample_article)
        
        assert result is False
    
    def test_get_articles_no_filters(self, db_storage, sample_article, sample_article_2):
        """Test retrieving all articles without filters."""
        db_storage.save_article(sample_article)
        db_storage.save_article(sample_article_2)
        
        articles = db_storage.get_articles()
        
        assert len(articles) == 2
        assert any(a.url == sample_article.url for a in articles)
        assert any(a.url == sample_article_2.url for a in articles)
    
    def test_get_articles_filter_by_entity(self, db_storage, sample_article, sample_article_2):
        """Test retrieving articles filtered by entity."""
        db_storage.save_article(sample_article)
        db_storage.save_article(sample_article_2)
        
        filters = ArticleFilters(entities=["Microsoft"])
        articles = db_storage.get_articles(filters)
        
        assert len(articles) == 1
        assert articles[0].url == sample_article.url
        assert "Microsoft" in articles[0].entity_tags
    
    def test_get_articles_filter_by_date_range(self, db_storage, sample_article, sample_article_2):
        """Test retrieving articles filtered by date range."""
        db_storage.save_article(sample_article)
        db_storage.save_article(sample_article_2)
        
        filters = ArticleFilters(
            start_date=datetime(2024, 1, 15),
            end_date=datetime(2024, 1, 15, 23, 59, 59)
        )
        articles = db_storage.get_articles(filters)
        
        assert len(articles) == 1
        assert articles[0].url == sample_article.url
    
    def test_get_articles_multi_entity_tags(self, db_storage, sample_article):
        """Test article with multiple entity tags is stored correctly."""
        db_storage.save_article(sample_article)
        
        articles = db_storage.get_articles()
        
        assert len(articles) == 1
        assert len(articles[0].entity_tags) == 2
        assert "Microsoft" in articles[0].entity_tags
        assert "Google" in articles[0].entity_tags


class TestCSVStorage:
    """Tests for CSVStorage class."""
    
    @pytest.fixture
    def csv_storage(self):
        """Create a CSVStorage instance with temporary file."""
        temp_file = tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.csv')
        temp_file.close()
        storage = CSVStorage(temp_file.name)
        yield storage
        # Cleanup
        if os.path.exists(temp_file.name):
            os.unlink(temp_file.name)
    
    def test_csv_storage_initialization(self, csv_storage):
        """Test CSVStorage initializes correctly and creates file."""
        assert os.path.exists(csv_storage.output_path)
    
    def test_csv_file_has_headers(self, csv_storage):
        """Test CSV file is created with proper headers."""
        with open(csv_storage.output_path, 'r', encoding='utf-8') as f:
            header = f.readline().strip()
        
        assert header == "Title,URL,Published Date,Entities,Summary,Source,Created At"
    
    def test_save_article_success(self, csv_storage, sample_article):
        """Test saving an article to CSV."""
        result = csv_storage.save_article(sample_article)
        
        assert result is True
    
    def test_save_article_duplicate(self, csv_storage, sample_article):
        """Test saving duplicate article returns True without adding duplicate."""
        csv_storage.save_article(sample_article)
        result = csv_storage.save_article(sample_article)
        
        assert result is True
        
        # Verify only one article in CSV
        articles = csv_storage.get_articles()
        assert len(articles) == 1
    
    def test_save_article_missing_title(self, csv_storage, sample_article):
        """Test saving article with empty title fails validation."""
        sample_article.title = ""
        result = csv_storage.save_article(sample_article)
        
        assert result is False
    
    def test_save_article_missing_url(self, csv_storage, sample_article):
        """Test saving article with empty URL fails validation."""
        sample_article.url = ""
        result = csv_storage.save_article(sample_article)
        
        assert result is False
    
    def test_save_article_missing_published_date(self, csv_storage, sample_article):
        """Test saving article with missing published_date fails validation."""
        sample_article.published_date = None
        result = csv_storage.save_article(sample_article)
        
        assert result is False
    
    def test_save_article_empty_entity_tags(self, csv_storage, sample_article):
        """Test saving article with empty entity_tags fails validation."""
        sample_article.entity_tags = []
        result = csv_storage.save_article(sample_article)
        
        assert result is False
    
    def test_save_article_empty_summary(self, csv_storage, sample_article):
        """Test saving article with empty summary fails validation."""
        sample_article.summary = ""
        result = csv_storage.save_article(sample_article)
        
        assert result is False
    
    def test_get_articles_no_filters(self, csv_storage, sample_article, sample_article_2):
        """Test retrieving all articles without filters."""
        csv_storage.save_article(sample_article)
        csv_storage.save_article(sample_article_2)
        
        articles = csv_storage.get_articles()
        
        assert len(articles) == 2
        assert any(a.url == sample_article.url for a in articles)
        assert any(a.url == sample_article_2.url for a in articles)
    
    def test_get_articles_filter_by_entity(self, csv_storage, sample_article, sample_article_2):
        """Test retrieving articles filtered by entity."""
        csv_storage.save_article(sample_article)
        csv_storage.save_article(sample_article_2)
        
        filters = ArticleFilters(entities=["Microsoft"])
        articles = csv_storage.get_articles(filters)
        
        assert len(articles) == 1
        assert articles[0].url == sample_article.url
        assert "Microsoft" in articles[0].entity_tags
    
    def test_get_articles_filter_by_date_range(self, csv_storage, sample_article, sample_article_2):
        """Test retrieving articles filtered by date range."""
        csv_storage.save_article(sample_article)
        csv_storage.save_article(sample_article_2)
        
        filters = ArticleFilters(
            start_date=datetime(2024, 1, 15),
            end_date=datetime(2024, 1, 15, 23, 59, 59)
        )
        articles = csv_storage.get_articles(filters)
        
        assert len(articles) == 1
        assert articles[0].url == sample_article.url
    
    def test_get_articles_multi_entity_tags(self, csv_storage, sample_article):
        """Test article with multiple entity tags stored as comma-separated."""
        csv_storage.save_article(sample_article)
        
        articles = csv_storage.get_articles()
        
        assert len(articles) == 1
        assert len(articles[0].entity_tags) == 2
        assert "Microsoft" in articles[0].entity_tags
        assert "Google" in articles[0].entity_tags
    
    def test_get_articles_empty_csv(self):
        """Test retrieving articles from empty CSV returns empty list."""
        temp_file = tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.csv')
        temp_file.close()
        storage = CSVStorage(temp_file.name)
        
        articles = storage.get_articles()
        
        assert len(articles) == 0
        
        # Cleanup
        os.unlink(temp_file.name)
