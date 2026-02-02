"""Storage layer for persisting processed articles."""
import logging
from abc import ABC, abstractmethod
from dataclasses import dataclass
from datetime import datetime
from typing import List, Optional


logger = logging.getLogger(__name__)


@dataclass
class ProcessedArticle:
    """Final article ready for storage with all required fields."""
    title: str
    url: str
    published_date: datetime  # or scrape_timestamp if unavailable
    entity_tags: List[str]
    summary: str
    source: str
    created_at: datetime


@dataclass
class ArticleFilters:
    """Filters for querying stored articles."""
    entities: Optional[List[str]] = None
    start_date: Optional[datetime] = None
    end_date: Optional[datetime] = None


class StorageLayer(ABC):
    """Abstract base class for article storage backends."""
    
    def _validate_article(self, article: ProcessedArticle) -> bool:
        """Validate that all required fields are present and non-empty.
        
        Args:
            article: ProcessedArticle to validate
            
        Returns:
            True if all required fields are valid, False otherwise
        """
        # Check title
        if not article.title or not article.title.strip():
            logger.error("Article validation failed: title is empty")
            return False
        
        # Check URL
        if not article.url or not article.url.strip():
            logger.error("Article validation failed: URL is empty")
            return False
        
        # Check published_date
        if not article.published_date:
            logger.error("Article validation failed: published_date is missing")
            return False
        
        # Check entity_tags
        if not article.entity_tags or len(article.entity_tags) == 0:
            logger.error("Article validation failed: entity_tags is empty")
            return False
        
        # Check summary
        if not article.summary or not article.summary.strip():
            logger.error("Article validation failed: summary is empty")
            return False
        
        return True
    
    @abstractmethod
    def save_article(self, article: ProcessedArticle) -> bool:
        """Save a processed article to storage.
        
        Args:
            article: ProcessedArticle to save
            
        Returns:
            True if save was successful, False otherwise
        """
        pass
    
    @abstractmethod
    def get_articles(self, filters: Optional[ArticleFilters] = None) -> List[ProcessedArticle]:
        """Retrieve articles from storage with optional filtering.
        
        Args:
            filters: Optional ArticleFilters to filter results
            
        Returns:
            List of ProcessedArticle instances matching the filters
        """
        pass



class DatabaseStorage(StorageLayer):
    """Database storage implementation using SQLAlchemy."""
    
    def __init__(self, database_url: str):
        """Initialize DatabaseStorage with a database connection.
        
        Args:
            database_url: Database connection URL (e.g., 'sqlite:///articles.db' or PostgreSQL URL)
        """
        from sqlalchemy import create_engine, Column, Integer, String, DateTime, Text, Table, ForeignKey
        from sqlalchemy.orm import declarative_base, sessionmaker, relationship
        
        self.database_url = database_url
        self.engine = create_engine(database_url)
        self.Base = declarative_base()
        
        # Define the articles table
        class Article(self.Base):
            __tablename__ = 'articles'
            
            id = Column(Integer, primary_key=True)
            title = Column(Text, nullable=False)
            url = Column(Text, nullable=False, unique=True)
            published_date = Column(DateTime, nullable=False)
            source = Column(Text, nullable=False)
            summary = Column(Text, nullable=False)
            created_at = Column(DateTime, nullable=False)
        
        # Define the article_entities association table
        class ArticleEntity(self.Base):
            __tablename__ = 'article_entities'
            
            id = Column(Integer, primary_key=True)
            article_id = Column(Integer, ForeignKey('articles.id'), nullable=False)
            entity = Column(Text, nullable=False)
        
        self.Article = Article
        self.ArticleEntity = ArticleEntity
        
        # Create tables
        self.Base.metadata.create_all(self.engine)
        
        # Create session factory
        self.Session = sessionmaker(bind=self.engine)
        
        logger.info(f"Initialized DatabaseStorage with URL: {database_url}")
    
    def save_article(self, article: ProcessedArticle) -> bool:
        """Save a processed article to the database.
        
        Args:
            article: ProcessedArticle to save
            
        Returns:
            True if save was successful, False otherwise
        """
        # Validate required fields
        if not self._validate_article(article):
            return False
        
        session = self.Session()
        try:
            # Check if article already exists (by URL)
            existing = session.query(self.Article).filter_by(url=article.url).first()
            if existing:
                logger.info(f"Article already exists in database: {article.url}")
                session.close()
                return True
            
            # Create article record
            db_article = self.Article(
                title=article.title,
                url=article.url,
                published_date=article.published_date,
                source=article.source,
                summary=article.summary,
                created_at=article.created_at
            )
            session.add(db_article)
            session.flush()  # Get the article ID
            
            # Create entity associations
            for entity in article.entity_tags:
                entity_record = self.ArticleEntity(
                    article_id=db_article.id,
                    entity=entity
                )
                session.add(entity_record)
            
            session.commit()
            logger.info(f"Successfully saved article to database: {article.title}")
            return True
        
        except Exception as e:
            session.rollback()
            logger.error(f"Failed to save article to database: {e}")
            return False
        finally:
            session.close()
    
    def get_articles(self, filters: Optional[ArticleFilters] = None) -> List[ProcessedArticle]:
        """Retrieve articles from the database with optional filtering.
        
        Args:
            filters: Optional ArticleFilters to filter results
            
        Returns:
            List of ProcessedArticle instances matching the filters
        """
        session = self.Session()
        try:
            # Start with base query
            query = session.query(self.Article)
            
            # Apply entity filter if specified
            if filters and filters.entities:
                # Join with article_entities and filter by entity
                query = query.join(self.ArticleEntity).filter(
                    self.ArticleEntity.entity.in_(filters.entities)
                ).distinct()
            
            # Apply date filters if specified
            if filters and filters.start_date:
                query = query.filter(self.Article.published_date >= filters.start_date)
            
            if filters and filters.end_date:
                query = query.filter(self.Article.published_date <= filters.end_date)
            
            # Execute query
            db_articles = query.all()
            
            # Convert to ProcessedArticle instances
            result = []
            for db_article in db_articles:
                # Get entity tags for this article
                entity_records = session.query(self.ArticleEntity).filter_by(
                    article_id=db_article.id
                ).all()
                entity_tags = [record.entity for record in entity_records]
                
                processed_article = ProcessedArticle(
                    title=db_article.title,
                    url=db_article.url,
                    published_date=db_article.published_date,
                    entity_tags=entity_tags,
                    summary=db_article.summary,
                    source=db_article.source,
                    created_at=db_article.created_at
                )
                result.append(processed_article)
            
            logger.info(f"Retrieved {len(result)} articles from database")
            return result
        
        except Exception as e:
            logger.error(f"Failed to retrieve articles from database: {e}")
            return []
        finally:
            session.close()



class CSVStorage(StorageLayer):
    """CSV file storage implementation."""
    
    def __init__(self, output_path: str):
        """Initialize CSVStorage with an output file path.
        
        Args:
            output_path: Path to the CSV file for storing articles
        """
        import os
        
        self.output_path = output_path
        
        # Ensure directory exists
        directory = os.path.dirname(output_path)
        if directory and not os.path.exists(directory):
            os.makedirs(directory)
        
        # Create file with headers if it doesn't exist or is empty
        if not os.path.exists(output_path) or os.path.getsize(output_path) == 0:
            self._create_csv_with_headers()
        
        logger.info(f"Initialized CSVStorage with output path: {output_path}")
    
    def _create_csv_with_headers(self):
        """Create CSV file with proper headers."""
        import csv
        
        with open(self.output_path, 'w', newline='', encoding='utf-8') as f:
            writer = csv.writer(f)
            writer.writerow(['Title', 'URL', 'Published Date', 'Entities', 'Summary', 'Source', 'Created At'])
        
        logger.info(f"Created CSV file with headers: {self.output_path}")
    
    def save_article(self, article: ProcessedArticle) -> bool:
        """Save a processed article to the CSV file.
        
        Args:
            article: ProcessedArticle to save
            
        Returns:
            True if save was successful, False otherwise
        """
        import csv
        
        # Validate required fields
        if not self._validate_article(article):
            return False
        
        try:
            # Check if article already exists (by URL)
            existing_articles = self.get_articles()
            if any(a.url == article.url for a in existing_articles):
                logger.info(f"Article already exists in CSV: {article.url}")
                return True
            
            # Append to CSV file
            with open(self.output_path, 'a', newline='', encoding='utf-8') as f:
                writer = csv.writer(f)
                writer.writerow([
                    article.title,
                    article.url,
                    article.published_date.isoformat(),
                    ','.join(article.entity_tags),  # Comma-separated entities
                    article.summary,
                    article.source,
                    article.created_at.isoformat()
                ])
            
            logger.info(f"Successfully saved article to CSV: {article.title}")
            return True
        
        except Exception as e:
            logger.error(f"Failed to save article to CSV: {e}")
            return False
    
    def get_articles(self, filters: Optional[ArticleFilters] = None) -> List[ProcessedArticle]:
        """Retrieve articles from the CSV file with optional filtering.
        
        Args:
            filters: Optional ArticleFilters to filter results
            
        Returns:
            List of ProcessedArticle instances matching the filters
        """
        import csv
        import os
        
        try:
            # Check if file exists
            if not os.path.exists(self.output_path):
                logger.warning(f"CSV file does not exist: {self.output_path}")
                return []
            
            result = []
            
            with open(self.output_path, 'r', newline='', encoding='utf-8') as f:
                reader = csv.DictReader(f)
                
                for row in reader:
                    try:
                        # Parse entity tags (comma-separated)
                        entity_tags = [e.strip() for e in row['Entities'].split(',') if e.strip()]
                        
                        # Parse dates
                        published_date = datetime.fromisoformat(row['Published Date'])
                        created_at = datetime.fromisoformat(row['Created At'])
                        
                        # Create ProcessedArticle
                        article = ProcessedArticle(
                            title=row['Title'],
                            url=row['URL'],
                            published_date=published_date,
                            entity_tags=entity_tags,
                            summary=row['Summary'],
                            source=row['Source'],
                            created_at=created_at
                        )
                        
                        # Apply filters
                        if filters:
                            # Entity filter
                            if filters.entities:
                                if not any(entity in article.entity_tags for entity in filters.entities):
                                    continue
                            
                            # Date filters
                            if filters.start_date and article.published_date < filters.start_date:
                                continue
                            
                            if filters.end_date and article.published_date > filters.end_date:
                                continue
                        
                        result.append(article)
                    except (KeyError, ValueError) as e:
                        logger.warning(f"Error parsing CSV row: {e}")
                        continue
            
            logger.info(f"Retrieved {len(result)} articles from CSV")
            return result
        
        except Exception as e:
            logger.error(f"Failed to retrieve articles from CSV: {e}")
            return []
