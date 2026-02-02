"""Configuration management for the news aggregation system."""
import os
from dataclasses import dataclass
from enum import Enum
from typing import Optional, List


class StorageType(Enum):
    """Storage backend types."""
    DATABASE = "database"
    CSV = "csv"
    WEB_UI = "web_ui"


@dataclass
class TestSet:
    """Represents a test set of company entities."""
    name: str
    entities: List[str]


@dataclass
class Config:
    """System configuration loaded from environment variables."""
    news_api_key: str
    ai_api_key: str
    ai_provider: str
    storage_type: StorageType
    database_url: Optional[str] = None
    output_path: Optional[str] = None


class ConfigurationManager:
    """Manages system configuration and test set selection."""
    
    # Predefined test sets
    TEST_SETS = [
        TestSet(name="Test Set 1: IT Services", entities=["TCS", "Wipro", "Infosys", "HCLTech"]),
        TestSet(name="Test Set 2: Telecom", entities=["Airtel", "Jio", "Vodafone Idea", "BSNL", "MTNL", "Tejas Networks"]),
        TestSet(name="Test Set 3: AI Companies", entities=["OpenAI", "Anthropic", "Google Deepmind", "Microsoft", "Meta"]),
        TestSet(name="Test Set 4: Tech Giants", entities=["Microsoft", "Google", "Apple", "Meta"]),
    ]
    
    @staticmethod
    def load_config() -> Config:
        """Load configuration from environment variables.
        
        Returns:
            Config: System configuration
            
        Raises:
            ValueError: If required environment variables are missing
        """
        news_api_key = os.getenv("NEWS_API_KEY")
        ai_api_key = os.getenv("AI_API_KEY")
        ai_provider = os.getenv("AI_PROVIDER", "openai")
        storage_type_str = os.getenv("STORAGE_TYPE", "csv")
        
        if not news_api_key:
            raise ValueError("Missing required environment variable: NEWS_API_KEY")
        if not ai_api_key:
            raise ValueError("Missing required environment variable: AI_API_KEY")
        
        try:
            storage_type = StorageType(storage_type_str.lower())
        except ValueError:
            raise ValueError(f"Invalid STORAGE_TYPE: {storage_type_str}. Must be one of: database, csv, web_ui")
        
        database_url = os.getenv("DATABASE_URL")
        output_path = os.getenv("OUTPUT_PATH", "output/articles.csv")
        
        return Config(
            news_api_key=news_api_key,
            ai_api_key=ai_api_key,
            ai_provider=ai_provider,
            storage_type=storage_type,
            database_url=database_url,
            output_path=output_path
        )
    
    @staticmethod
    def validate_api_keys() -> bool:
        """Validate that required API keys are present.
        
        Returns:
            bool: True if all required API keys are present
        """
        return bool(os.getenv("NEWS_API_KEY") and os.getenv("AI_API_KEY"))
    
    @staticmethod
    def select_test_set() -> TestSet:
        """Prompt user to select a test set.
        
        Returns:
            TestSet: Selected test set
        """
        print("\n=== News Aggregation System ===")
        print("\nPlease select a test set:\n")
        
        for i, test_set in enumerate(ConfigurationManager.TEST_SETS, 1):
            print(f"{i}. {test_set.name}")
            print(f"   Entities: {', '.join(test_set.entities)}\n")
        
        while True:
            try:
                choice = input("Enter your choice (1-4): ").strip()
                choice_num = int(choice)
                
                if 1 <= choice_num <= len(ConfigurationManager.TEST_SETS):
                    selected = ConfigurationManager.TEST_SETS[choice_num - 1]
                    print(f"\nSelected: {selected.name}")
                    return selected
                else:
                    print(f"Please enter a number between 1 and {len(ConfigurationManager.TEST_SETS)}")
            except ValueError:
                print("Please enter a valid number")
            except (EOFError, KeyboardInterrupt):
                print("\nExiting...")
                raise SystemExit(1)
