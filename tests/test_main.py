"""Tests for main entry point."""
import os
import sys
from unittest.mock import patch, MagicMock
import pytest
from main import parse_arguments, main


class TestParseArguments:
    """Tests for command-line argument parsing."""
    
    def test_parse_arguments_no_args(self):
        """Test parsing with no arguments."""
        with patch('sys.argv', ['main.py']):
            args = parse_arguments()
            assert args.storage_type is None
            assert args.test_set is None
            assert args.output_path is None
            assert args.database_url is None
    
    def test_parse_arguments_storage_type(self):
        """Test parsing --storage-type argument."""
        with patch('sys.argv', ['main.py', '--storage-type', 'csv']):
            args = parse_arguments()
            assert args.storage_type == 'csv'
    
    def test_parse_arguments_test_set(self):
        """Test parsing --test-set argument."""
        with patch('sys.argv', ['main.py', '--test-set', '1']):
            args = parse_arguments()
            assert args.test_set == 1
    
    def test_parse_arguments_output_path(self):
        """Test parsing --output-path argument."""
        with patch('sys.argv', ['main.py', '--output-path', 'custom/path.csv']):
            args = parse_arguments()
            assert args.output_path == 'custom/path.csv'
    
    def test_parse_arguments_database_url(self):
        """Test parsing --database-url argument."""
        with patch('sys.argv', ['main.py', '--database-url', 'sqlite:///test.db']):
            args = parse_arguments()
            assert args.database_url == 'sqlite:///test.db'
    
    def test_parse_arguments_all_args(self):
        """Test parsing all arguments together."""
        with patch('sys.argv', [
            'main.py',
            '--storage-type', 'database',
            '--test-set', '3',
            '--output-path', 'output.csv',
            '--database-url', 'postgresql://localhost/test'
        ]):
            args = parse_arguments()
            assert args.storage_type == 'database'
            assert args.test_set == 3
            assert args.output_path == 'output.csv'
            assert args.database_url == 'postgresql://localhost/test'


class TestMain:
    """Tests for main function."""
    
    def test_main_missing_api_keys(self, monkeypatch):
        """Test main function fails when API keys are missing."""
        # Mock load_dotenv to prevent loading from .env file
        with patch('main.load_dotenv'):
            # Clear environment variables
            monkeypatch.delenv('NEWS_API_KEY', raising=False)
            monkeypatch.delenv('AI_API_KEY', raising=False)
            
            # Use --test-set flag to avoid interactive prompt
            with patch('sys.argv', ['main.py', '--test-set', '1']):
                exit_code = main()
                assert exit_code == 1
    
    def test_main_with_api_keys_and_test_set(self, monkeypatch, tmp_path):
        """Test main function with valid API keys and command-line test set."""
        # Set up environment
        monkeypatch.setenv('NEWS_API_KEY', 'test_news_key')
        monkeypatch.setenv('AI_API_KEY', 'test_ai_key')
        monkeypatch.setenv('STORAGE_TYPE', 'csv')
        
        output_file = tmp_path / "test_articles.csv"
        monkeypatch.setenv('OUTPUT_PATH', str(output_file))
        
        # Mock the pipeline components to avoid actual API calls
        with patch('main.NewsCollector') as mock_collector, \
             patch('main.EntityClassifier') as mock_classifier, \
             patch('main.ArticleScraper') as mock_scraper, \
             patch('main.AISummarizer') as mock_summarizer, \
             patch('main.CSVStorage') as mock_storage, \
             patch('main.PipelineOrchestrator') as mock_orchestrator, \
             patch('sys.argv', ['main.py', '--test-set', '1']):
            
            # Mock the orchestrator run method
            mock_result = MagicMock()
            mock_result.total_collected = 10
            mock_result.total_scraped = 8
            mock_result.total_classified = 7
            mock_result.total_summarized = 7
            mock_result.total_stored = 7
            mock_result.errors = []
            
            mock_orchestrator_instance = MagicMock()
            mock_orchestrator_instance.run.return_value = mock_result
            mock_orchestrator.return_value = mock_orchestrator_instance
            
            # Run main
            exit_code = main()
            
            # Verify success
            assert exit_code == 0
            
            # Verify components were initialized
            mock_collector.assert_called_once()
            mock_classifier.assert_called_once()
            mock_scraper.assert_called_once()
            mock_summarizer.assert_called_once()
            mock_storage.assert_called_once()
            mock_orchestrator.assert_called_once()
            
            # Verify orchestrator was run
            mock_orchestrator_instance.run.assert_called_once()
