"""Main entry point for the news aggregation system."""
import os
import sys
import argparse
import logging
from dotenv import load_dotenv
from src.config import ConfigurationManager, Config, TestSet, StorageType
from src.news_collector import NewsCollector
from src.entity_classifier import EntityClassifier
from src.article_scraper import ArticleScraper
from src.ai_summarizer import AISummarizer, AIProvider
from src.storage_layer import DatabaseStorage, CSVStorage
from src.pipeline_orchestrator import PipelineOrchestrator


# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def parse_arguments():
    """Parse command-line arguments.
    
    Returns:
        Parsed arguments namespace
    """
    parser = argparse.ArgumentParser(
        description='News Aggregation System - Collect, classify, and summarize financial news'
    )
    
    parser.add_argument(
        '--storage-type',
        choices=['database', 'csv', 'web-ui'],
        help='Storage backend type (overrides STORAGE_TYPE env var)'
    )
    
    parser.add_argument(
        '--test-set',
        type=int,
        choices=[1, 2, 3, 4],
        help='Test set number (1-4) to skip interactive selection'
    )
    
    parser.add_argument(
        '--output-path',
        help='Output path for CSV storage (overrides OUTPUT_PATH env var)'
    )
    
    parser.add_argument(
        '--database-url',
        help='Database connection URL (overrides DATABASE_URL env var)'
    )
    
    return parser.parse_args()


def main():
    """Main entry point."""
    # Parse command-line arguments
    args = parse_arguments()
    
    # Load environment variables from .env file
    load_dotenv()
    
    # Override environment variables with command-line arguments
    if args.storage_type:
        os.environ['STORAGE_TYPE'] = args.storage_type
    
    if args.output_path:
        os.environ['OUTPUT_PATH'] = args.output_path
    
    if args.database_url:
        os.environ['DATABASE_URL'] = args.database_url
    
    # Validate API keys and fail fast if missing
    if not ConfigurationManager.validate_api_keys():
        print("\n❌ Error: Missing required API keys!")
        print("\nPlease ensure the following environment variables are set:")
        print("  - NEWS_API_KEY")
        print("  - AI_API_KEY")
        print("\nYou can set these in a .env file (see .env.example for reference)")
        return 1
    
    # Load configuration
    try:
        config = ConfigurationManager.load_config()
        print(f"\n✓ Configuration loaded successfully")
        print(f"  Storage Type: {config.storage_type.value}")
        if config.storage_type.value == "csv":
            print(f"  Output Path: {config.output_path}")
        elif config.storage_type.value == "database":
            print(f"  Database URL: {config.database_url}")
    except ValueError as e:
        print(f"\n❌ Configuration Error: {e}")
        return 1
    
    # Select test set (interactive or from command-line)
    try:
        if args.test_set:
            # Use command-line specified test set
            test_set = ConfigurationManager.TEST_SETS[args.test_set - 1]
            print(f"\n✓ Test set selected: {test_set.name}")
            print(f"  Tracking entities: {', '.join(test_set.entities)}")
        else:
            # Interactive selection
            test_set = ConfigurationManager.select_test_set()
            print(f"\n✓ Test set selected: {test_set.name}")
            print(f"  Tracking entities: {', '.join(test_set.entities)}")
    except (SystemExit, IndexError):
        return 1
    
    # Initialize all components
    print("\n" + "=" * 60)
    print("Initializing pipeline components...")
    print("=" * 60)
    
    try:
        # Initialize NewsCollector
        collector = NewsCollector(api_key=config.news_api_key)
        print("✓ NewsCollector initialized")
        
        # Initialize EntityClassifier
        classifier = EntityClassifier(test_set=test_set)
        print("✓ EntityClassifier initialized")
        
        # Initialize ArticleScraper
        scraper = ArticleScraper()
        print("✓ ArticleScraper initialized")
        
        # Initialize AISummarizer
        # Map provider string to AIProvider enum
        provider_map = {
            "openai": AIProvider.OPENAI,
            "claude": AIProvider.CLAUDE,
            "gemini": AIProvider.GEMINI,
            "groq": AIProvider.GROQ
        }
        ai_provider = provider_map.get(config.ai_provider.lower(), AIProvider.OPENAI)
        
        summarizer = AISummarizer(
            api_key=config.ai_api_key,
            provider=ai_provider
        )
        print(f"✓ AISummarizer initialized (provider: {config.ai_provider})")
        
        # Initialize StorageLayer
        if config.storage_type == StorageType.DATABASE:
            if not config.database_url:
                print("\n❌ Error: DATABASE_URL is required for database storage")
                return 1
            storage = DatabaseStorage(database_url=config.database_url)
        elif config.storage_type == StorageType.CSV:
            storage = CSVStorage(output_path=config.output_path)
        else:
            print(f"\n❌ Error: Storage type '{config.storage_type.value}' not yet implemented")
            return 1
        
        print(f"✓ {config.storage_type.value.upper()} storage initialized")
        
        # Initialize PipelineOrchestrator
        orchestrator = PipelineOrchestrator(
            config=config,
            test_set=test_set,
            collector=collector,
            classifier=classifier,
            scraper=scraper,
            summarizer=summarizer,
            storage=storage
        )
        print("✓ PipelineOrchestrator initialized")
        
    except Exception as e:
        print(f"\n❌ Error initializing components: {e}")
        logger.exception("Component initialization failed")
        return 1
    
    # Run pipeline orchestrator
    print("\n" + "=" * 60)
    print("Starting news aggregation pipeline...")
    print("=" * 60 + "\n")
    
    try:
        result = orchestrator.run()
        
        # Display pipeline results and statistics
        print("\n" + "=" * 60)
        print("PIPELINE EXECUTION SUMMARY")
        print("=" * 60)
        print(f"\n📊 Statistics:")
        print(f"  Articles Collected:   {result.total_collected}")
        print(f"  Articles Scraped:     {result.total_scraped}")
        print(f"  Articles Classified:  {result.total_classified}")
        print(f"  Articles Summarized:  {result.total_summarized}")
        print(f"  Articles Stored:      {result.total_stored}")
        print(f"  Total Errors:         {len(result.errors)}")
        
        if result.errors:
            print(f"\n⚠️  Errors by stage:")
            error_counts = {}
            for error in result.errors:
                error_counts[error.stage] = error_counts.get(error.stage, 0) + 1
            for stage, count in sorted(error_counts.items()):
                print(f"    {stage.capitalize()}: {count}")
        
        # Success rate
        if result.total_collected > 0:
            success_rate = (result.total_stored / result.total_collected) * 100
            print(f"\n✓ Success Rate: {success_rate:.1f}%")
        
        # Storage location info
        print(f"\n📁 Storage Location:")
        if config.storage_type == StorageType.CSV:
            print(f"  CSV File: {config.output_path}")
        elif config.storage_type == StorageType.DATABASE:
            print(f"  Database: {config.database_url}")
        
        print("\n" + "=" * 60)
        print("Pipeline execution completed successfully!")
        print("=" * 60 + "\n")
        
        return 0
        
    except Exception as e:
        print(f"\n❌ Pipeline execution failed: {e}")
        logger.exception("Pipeline execution error")
        return 1


if __name__ == "__main__":
    sys.exit(main())
