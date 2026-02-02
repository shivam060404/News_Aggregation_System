"""Unit tests for configuration management."""
import os
import pytest
from src.config import ConfigurationManager, Config, TestSet, StorageType


class TestConfigurationManager:
    """Tests for ConfigurationManager class."""
    
    def test_load_config_success(self, monkeypatch):
        """Test successful configuration loading."""
        monkeypatch.setenv("NEWS_API_KEY", "test_news_key")
        monkeypatch.setenv("AI_API_KEY", "test_ai_key")
        monkeypatch.setenv("STORAGE_TYPE", "csv")
        monkeypatch.setenv("OUTPUT_PATH", "test_output.csv")
        
        config = ConfigurationManager.load_config()
        
        assert config.news_api_key == "test_news_key"
        assert config.ai_api_key == "test_ai_key"
        assert config.storage_type == StorageType.CSV
        assert config.output_path == "test_output.csv"
    
    def test_load_config_missing_news_api_key(self, monkeypatch):
        """Test configuration loading fails without NEWS_API_KEY."""
        monkeypatch.delenv("NEWS_API_KEY", raising=False)
        monkeypatch.setenv("AI_API_KEY", "test_ai_key")
        
        with pytest.raises(ValueError, match="Missing required environment variable: NEWS_API_KEY"):
            ConfigurationManager.load_config()
    
    def test_load_config_missing_ai_api_key(self, monkeypatch):
        """Test configuration loading fails without AI_API_KEY."""
        monkeypatch.setenv("NEWS_API_KEY", "test_news_key")
        monkeypatch.delenv("AI_API_KEY", raising=False)
        
        with pytest.raises(ValueError, match="Missing required environment variable: AI_API_KEY"):
            ConfigurationManager.load_config()
    
    def test_load_config_invalid_storage_type(self, monkeypatch):
        """Test configuration loading fails with invalid storage type."""
        monkeypatch.setenv("NEWS_API_KEY", "test_news_key")
        monkeypatch.setenv("AI_API_KEY", "test_ai_key")
        monkeypatch.setenv("STORAGE_TYPE", "invalid")
        
        with pytest.raises(ValueError, match="Invalid STORAGE_TYPE"):
            ConfigurationManager.load_config()
    
    def test_load_config_default_storage_type(self, monkeypatch):
        """Test configuration uses default storage type when not specified."""
        monkeypatch.setenv("NEWS_API_KEY", "test_news_key")
        monkeypatch.setenv("AI_API_KEY", "test_ai_key")
        monkeypatch.delenv("STORAGE_TYPE", raising=False)
        
        config = ConfigurationManager.load_config()
        
        assert config.storage_type == StorageType.CSV
    
    def test_validate_api_keys_success(self, monkeypatch):
        """Test API key validation succeeds when keys are present."""
        monkeypatch.setenv("NEWS_API_KEY", "test_news_key")
        monkeypatch.setenv("AI_API_KEY", "test_ai_key")
        
        assert ConfigurationManager.validate_api_keys() is True
    
    def test_validate_api_keys_missing(self, monkeypatch):
        """Test API key validation fails when keys are missing."""
        monkeypatch.delenv("NEWS_API_KEY", raising=False)
        monkeypatch.delenv("AI_API_KEY", raising=False)
        
        assert ConfigurationManager.validate_api_keys() is False
    
    def test_test_sets_defined(self):
        """Test that all 4 test sets are defined."""
        assert len(ConfigurationManager.TEST_SETS) == 4
    
    def test_test_set_1_entities(self):
        """Test Test Set 1 has correct entities."""
        test_set = ConfigurationManager.TEST_SETS[0]
        assert test_set.entities == ["TCS", "Wipro", "Infosys", "HCLTech"]
    
    def test_test_set_2_entities(self):
        """Test Test Set 2 has correct entities."""
        test_set = ConfigurationManager.TEST_SETS[1]
        assert test_set.entities == ["Airtel", "Jio", "Vodafone Idea", "BSNL", "MTNL", "Tejas Networks"]
    
    def test_test_set_3_entities(self):
        """Test Test Set 3 has correct entities."""
        test_set = ConfigurationManager.TEST_SETS[2]
        assert test_set.entities == ["OpenAI", "Anthropic", "Google Deepmind", "Microsoft", "Meta"]
    
    def test_test_set_4_entities(self):
        """Test Test Set 4 has correct entities."""
        test_set = ConfigurationManager.TEST_SETS[3]
        assert test_set.entities == ["Microsoft", "Google", "Apple", "Meta"]
