"""Entity classification component for tagging articles with company entities."""
import logging
from typing import List
from src.config import TestSet
from src.news_collector import RawArticle


logger = logging.getLogger(__name__)


class EntityClassifier:
    """Classifies articles by extracting and matching company entities."""
    
    def __init__(self, test_set: TestSet):
        """Initialize the EntityClassifier with a test set.
        
        Args:
            test_set: TestSet containing the entities to match against
        """
        self.test_set = test_set
        # Store lowercase versions for case-insensitive matching
        self.entities_lower = [entity.lower() for entity in test_set.entities]
    
    def classify(self, article: RawArticle, full_content: str) -> List[str]:
        """Extract entities from article text and return matching entity tags.
        
        Performs case-insensitive matching of entities in both the article title
        and full content. Returns all matching entities from the test set.
        
        Args:
            article: RawArticle with title and metadata
            full_content: Full article text content
            
        Returns:
            List of matching entity names from the test set (original case).
            Returns empty list if no entities match.
        """
        return self._extract_entities(article, full_content)
    
    def should_include(self, article: RawArticle, full_content: str) -> bool:
        """Determine if an article should be included based on entity matching.
        
        Args:
            article: RawArticle with title and metadata
            full_content: Full article text content
            
        Returns:
            True if article mentions at least one entity from test set, False otherwise
        """
        entities = self.classify(article, full_content)
        return len(entities) > 0
    
    def _extract_entities(self, article: RawArticle, full_content: str) -> List[str]:
        """Extract all matching entities from article text.
        
        Searches for entity mentions in both title and full content using
        case-insensitive matching. Returns all entities that match.
        
        Args:
            article: RawArticle with title and metadata
            full_content: Full article text content
            
        Returns:
            List of matching entity names (original case from test set)
        """
        # Combine title and content for searching
        text_to_search = f"{article.title} {full_content}".lower()
        
        matched_entities = []
        
        # Check each entity from the test set
        for i, entity_lower in enumerate(self.entities_lower):
            # Case-insensitive search
            if entity_lower in text_to_search:
                # Return the original case entity name from test set
                matched_entities.append(self.test_set.entities[i])
        
        if matched_entities:
            logger.debug(f"Article '{article.title[:50]}...' matched entities: {', '.join(matched_entities)}")
        else:
            logger.debug(f"Article '{article.title[:50]}...' matched no entities")
        
        return matched_entities
