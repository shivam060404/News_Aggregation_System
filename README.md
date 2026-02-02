# News Aggregation System

A Python-based news aggregation system that collects financial news articles, classifies them by company entities, and generates AI-powered summaries. The system focuses on recent news (last 7 days) for a user-selected set of companies, providing organized and summarized information through a chosen storage method.

## Features

- Collects recent news (last 7 days) from public news APIs
- Classifies articles by company entities with multi-entity tagging
- Extracts full article content from source URLs
- Generates AI-powered summaries (30-40 words)
- Supports multiple storage backends (Database, CSV)
- Graceful error handling - individual failures don't stop the pipeline
- Comprehensive pipeline statistics and error reporting

## Prerequisites

- Python 3.8 or higher
- pip package manager
- API keys for:
  - News API (get from [NewsAPI.org](https://newsapi.org/register))
  - AI provider (OpenAI, Anthropic, Google Gemini, or Groq)

## Setup Instructions

### 1. Install Dependencies

Clone the repository and install required packages:

```bash
git clone <repository-url>
cd news-aggregation-system
pip install -r requirements.txt
```

### 2. Configure Environment Variables

Copy the example environment file:

```bash
cp .env.example .env
```

Edit the `.env` file and add your API keys:

```bash
# Required
NEWS_API_KEY=your_news_api_key_here
AI_API_KEY=your_ai_api_key_here

# Optional
STORAGE_TYPE=csv
OUTPUT_PATH=output/articles.csv
```

See the [Configuration](#configuration) section below for all available options.

### 3. Run the System

Start the news aggregation pipeline:

```bash
python main.py
```

The system will:
1. Validate your API keys (fails fast if missing)
2. Prompt you to select a test set
3. Initialize all pipeline components
4. Collect, classify, scrape, summarize, and store news articles
5. Display execution statistics

## Configuration

### Environment Variables

The system uses environment variables for configuration. All variables can be set in the `.env` file:

**Required:**
- `NEWS_API_KEY` - API key for news source (NewsAPI.org)
- `AI_API_KEY` - API key for AI summarization provider

**Optional:**
- `STORAGE_TYPE` - Storage backend: `database` or `csv` (default: `csv`)
- `OUTPUT_PATH` - Path for CSV output (default: `output/articles.csv`)
- `DATABASE_URL` - Database connection string (required if `STORAGE_TYPE=database`)
  - PostgreSQL example: `postgresql://user:password@localhost:5432/news_db`
  - SQLite example: `sqlite:///news.db`
- `AI_PROVIDER` - AI provider: `openai`, `claude`, `gemini`, or `groq` (default: `openai`)

### Command-Line Options

Override environment variables with command-line arguments:

```bash
python main.py [OPTIONS]
```

**Available Options:**
- `--storage-type {database,csv,web-ui}` - Storage backend type
- `--test-set {1,2,3,4}` - Test set number (skips interactive selection)
- `--output-path PATH` - Output path for CSV storage
- `--database-url URL` - Database connection URL
- `-h, --help` - Show help message

**Examples:**

Run with CSV storage and test set 1:
```bash
python main.py --storage-type csv --test-set 1
```

Run with database storage and test set 3:
```bash
python main.py --storage-type database --test-set 3 --database-url sqlite:///news.db
```

Run with custom CSV output path:
```bash
python main.py --output-path data/my_articles.csv
```

## Test Set Selection

When you run the system, you'll be prompted to select one of four predefined test sets. Each test set focuses on a specific industry segment:

**Test Set 1: IT Services**
- Companies: TCS, Wipro, Infosys, HCLTech
- Focus: Indian IT services companies

**Test Set 2: Telecom**
- Companies: Airtel, Jio, Vodafone Idea, BSNL, MTNL, Tejas Networks
- Focus: Telecommunications companies

**Test Set 3: AI Companies**
- Companies: OpenAI, Anthropic, Google Deepmind, Microsoft, Meta
- Focus: Artificial intelligence and research companies

**Test Set 4: Tech Giants**
- Companies: Microsoft, Google, Apple, Meta
- Focus: Major technology companies

The selected test set determines which companies the system will track. Articles are classified by entity, and articles mentioning multiple entities from your test set will be tagged with all relevant entities.

To skip interactive selection, use the `--test-set` flag:
```bash
python main.py --test-set 1  # Selects IT Services
```

## Accessing and Viewing Aggregated News Output

### CSV Storage (Default)

When using CSV storage, articles are saved to the specified output path (default: `output/articles.csv`).

**Viewing CSV Output:**

1. Open the CSV file in Excel, Google Sheets, or any spreadsheet application
2. The CSV contains the following columns:
   - `Title` - Article headline
   - `URL` - Source article URL
   - `Published Date` - Publication date/time
   - `Entities` - Comma-separated list of company tags
   - `Summary` - AI-generated 30-40 word summary
   - `Source` - News source name
   - `Created At` - Timestamp when article was processed

**Filtering and Sorting:**
- Use Excel's filter feature to view articles for specific companies
- Sort by published date to see the most recent articles
- Search for keywords in titles or summaries

### Database Storage

When using database storage, articles are stored in a relational database with two tables:

**Schema:**
- `articles` table - Main article data (title, URL, published_date, summary, source)
- `article_entities` table - Entity tags for each article (many-to-many relationship)

**Querying the Database:**

Connect to your database using any SQL client and run queries:

```sql
-- Get all articles for a specific entity
SELECT a.title, a.published_date, a.summary, a.url
FROM articles a
JOIN article_entities ae ON a.id = ae.article_id
WHERE ae.entity = 'Microsoft'
ORDER BY a.published_date DESC;

-- Get articles mentioning multiple entities
SELECT a.title, GROUP_CONCAT(ae.entity) as entities
FROM articles a
JOIN article_entities ae ON a.id = ae.article_id
GROUP BY a.id
HAVING COUNT(DISTINCT ae.entity) > 1;

-- Get article count by entity
SELECT entity, COUNT(*) as article_count
FROM article_entities
GROUP BY entity
ORDER BY article_count DESC;
```

**Database Tools:**
- PostgreSQL: Use pgAdmin, DBeaver, or psql command-line
- SQLite: Use DB Browser for SQLite, DBeaver, or sqlite3 command-line

## Pipeline Architecture

The system follows a modular pipeline architecture:

```
Configuration → News Collection → Entity Classification → 
Article Scraping → AI Summarization → Storage
```

**Components:**
1. **Configuration Manager** - Loads settings and manages test set selection
2. **News Collector** - Fetches articles from news APIs (7-day window)
3. **Entity Classifier** - Tags articles with relevant company entities
4. **Article Scraper** - Extracts full content from article URLs
5. **AI Summarizer** - Generates 30-40 word summaries
6. **Storage Layer** - Persists articles (CSV or Database)
7. **Pipeline Orchestrator** - Coordinates all components

## Troubleshooting

### Missing API Keys

**Error:** `❌ Error: Missing required API keys!`

**Solution:**
1. Ensure you have a `.env` file in the project root
2. Verify `NEWS_API_KEY` and `AI_API_KEY` are set in `.env`
3. Check that the `.env` file has no syntax errors
4. Restart the application after updating `.env`

### News API Rate Limits

**Error:** API rate limit errors in pipeline statistics

**Solution:**
- Free NewsAPI.org accounts have 100 requests/day limit
- Upgrade to a paid plan for higher limits
- The system handles rate limits gracefully and continues processing
- Check error logs for specific rate limit messages

### AI API Errors

**Error:** Summarization failures in pipeline statistics

**Solution:**
- Verify your AI API key is valid and has available credits
- Check your API provider's rate limits and quotas
- OpenAI: https://platform.openai.com/usage
- Anthropic: https://console.anthropic.com/
- The system continues processing even if some summaries fail

### Scraping Failures

**Error:** High scraping failure count in pipeline statistics

**Solution:**
- Some websites block automated scraping (paywalls, JavaScript-heavy sites)
- This is expected behavior - the system logs errors and continues
- Check error logs for specific URLs that failed
- Consider using alternative news sources if many articles fail

### Database Connection Errors

**Error:** `❌ Error: DATABASE_URL is required for database storage`

**Solution:**
1. Set `DATABASE_URL` in your `.env` file
2. Verify the database connection string format:
   - PostgreSQL: `postgresql://user:password@host:port/database`
   - SQLite: `sqlite:///path/to/database.db`
3. Ensure the database server is running (for PostgreSQL)
4. Check database credentials and permissions

### CSV File Not Created

**Error:** CSV output file not found

**Solution:**
1. Check that the output directory exists (create `output/` folder)
2. Verify write permissions for the output path
3. Check the `OUTPUT_PATH` setting in `.env` or command-line
4. Look for error messages in the pipeline execution log

### No Articles Collected

**Error:** `Articles Collected: 0`

**Solution:**
- The news API may not have recent articles for your selected entities
- Try a different test set with more popular companies
- Check that your NEWS_API_KEY is valid
- Verify the 7-day window includes recent news for those companies

### Import Errors

**Error:** `ModuleNotFoundError` or import errors

**Solution:**
1. Ensure all dependencies are installed: `pip install -r requirements.txt`
2. Verify you're using Python 3.8 or higher: `python --version`
3. Check that you're in the correct directory
4. Try reinstalling dependencies: `pip install --upgrade -r requirements.txt`

## Running Tests

Run the complete test suite:

```bash
pytest
```

Run tests with verbose output:

```bash
pytest -v
```

Run tests with coverage report:

```bash
pytest --cov=src tests/
```

Run specific test file:

```bash
pytest tests/test_config.py
```

## Code Quality Checks

Run code quality and security checks:

```bash
python check_code_quality.py
```

This script verifies:
- No hardcoded API keys in source code
- .env is properly ignored in .gitignore
- .env.example has placeholder values only
- Environment variables are used correctly

Run this before committing code to ensure security best practices.

## Project Structure

```
news-aggregation-system/
├── src/                          # Source code
│   ├── config.py                # Configuration management
│   ├── news_collector.py        # News API integration
│   ├── entity_classifier.py     # Entity classification
│   ├── article_scraper.py       # Content extraction
│   ├── ai_summarizer.py         # AI summarization
│   ├── storage_layer.py         # Storage backends
│   ├── pipeline_orchestrator.py # Pipeline coordination
│   └── __init__.py
├── tests/                        # Test files
│   ├── test_config.py
│   ├── test_news_collector.py
│   ├── test_entity_classifier.py
│   ├── test_article_scraper.py
│   ├── test_ai_summarizer.py
│   ├── test_storage_layer.py
│   ├── test_pipeline_orchestrator.py
│   ├── test_main.py
│   └── __init__.py
├── output/                       # Default CSV output directory
├── .env.example                 # Example environment variables
├── .env                         # Your environment variables (not in git)
├── requirements.txt             # Python dependencies
├── main.py                      # Main entry point
└── README.md                    # This file
```

## License

MIT License
