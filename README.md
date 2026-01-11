# Company Contact Scraper

A production-grade Python scraping pipeline for discovering companies hiring for software development roles and extracting their contact information.

## Features

- **Multi-source discovery**: Google search, job boards, startup directories
- **Intelligent email extraction**: Regex, mailto links, obfuscated patterns, JSON payloads
- **Rate limiting & robots.txt compliance**: Configurable delays, user-agent rotation
- **Headless browser support**: For JavaScript-heavy sites (optional Playwright)
- **Deduplication**: Stable hashing for companies and emails
- **Dual output**: CSV and JSON with timestamped filenames and manifest
- **Graceful shutdown**: Partial results saved on interrupt
- **Modular architecture**: Easy to add new sources

## Quick Start

### Prerequisites

- Python 3.11+
- pip

### Installation

```bash
# Clone or copy the project
cd jobs

# Create virtual environment (recommended)
python -m venv venv
venv\Scripts\activate  # Windows
# source venv/bin/activate  # Linux/Mac

# Install dependencies
pip install -r requirements.txt

# (Optional) For JavaScript-heavy sites
pip install playwright
playwright install chromium
```

### Configuration

```bash
# Copy example config
copy .env.example .env

# Edit .env with your settings (optional)
```

### Basic Usage

```bash
# Search Berlin for software developers (default roles)
python scrape_companies.py --location "Berlin, Germany"

# Multiple locations
python scrape_companies.py -l "Berlin, Germany" -l "Munich, Germany"

# Limit results
python scrape_companies.py -l "Berlin, Germany" --max-companies 300

# With verbose logging
python scrape_companies.py -l "Berlin, Germany" -v

# Custom roles
python scrape_companies.py -l "Berlin" --role "python developer" --role "devops engineer"

# Enable headless browser for JS sites
python scrape_companies.py -l "Berlin, Germany" --use-headless
```

## CLI Options

| Option | Short | Description |
|--------|-------|-------------|
| `--location` | `-l` | Location to search (required, multiple allowed) |
| `--role` | `-r` | Target role (multiple allowed, has defaults) |
| `--max-companies` | `-m` | Maximum companies to discover (default: 100) |
| `--use-headless` | `-h` | Enable headless browser |
| `--verbose` | `-v` | Enable verbose logging |
| `--concurrency` | `-c` | Max concurrent requests (default: 5) |
| `--output-dir` | `-o` | Custom output directory |

## Output

Results are saved to `data/company_contacts/`:

```
data/company_contacts/
├── companies_berlin_germany_20250110_143052.csv
├── companies_berlin_germany_20250110_143052.json
└── manifest.json
```

### CSV Columns

- `company_name`, `location`, `website`, `careers_url`, `linkedin_url`
- `hiring_roles`, `best_email`, `best_email_confidence`, `all_emails`
- `job_description`, `source_url`, `discovered_at`

### JSON Structure

```json
{
  "metadata": {
    "created_at": "2025-01-10T14:30:52",
    "location": "Berlin, Germany",
    "total_companies": 150,
    "total_emails": 89
  },
  "companies": [
    {
      "name": "Tech Startup GmbH",
      "location": "Berlin, Germany",
      "emails": [
        {
          "email": "hr@techstartup.com",
          "confidence": "high",
          "is_hr_contact": true
        }
      ]
    }
  ]
}
```

## Project Structure

```
jobs/
├── scrape_companies.py    # CLI entry point
├── pipeline.py            # Main orchestrator
├── config.py              # Configuration management
├── models.py              # Data models
├── requirements.txt       # Dependencies
├── .env.example           # Config template
│
├── discovery/             # Source plugins
│   ├── base_source.py     # Plugin interface
│   ├── google_source.py   # Google search
│   ├── job_board_source.py# Indeed, Glassdoor, etc.
│   └── company_crawler.py # Deep website crawler
│
├── fetcher/               # HTTP handling
│   ├── page_fetcher.py    # Requests with retries
│   └── headless_fetcher.py# Playwright browser
│
├── parsers/               # HTML parsing
│   └── html_parser.py     # BeautifulSoup wrapper
│
├── extractors/            # Email extraction
│   └── email_extractor.py # Regex & heuristics
│
├── storage/               # Data persistence
│   └── data_storage.py    # CSV/JSON output
│
├── utils/                 # Utilities
│   └── logging_utils.py   # Logging & progress
│
└── tests/                 # Unit tests
    ├── test_email_extractor.py
    ├── test_storage.py
    └── test_models.py
```

## Adding New Sources

Create a new source by extending `BaseSource`:

```python
from discovery.base_source import BaseSource, register_source

class MyCustomSource(BaseSource):
    def __init__(self):
        super().__init__(
            name="my_source",
            base_url="https://mysource.com",
            requires_js=False,
        )
    
    def search(self, location, roles, max_results):
        # Yield Company objects
        pass
    
    def get_company_details(self, company):
        # Enrich company with details
        return company

# Register in pipeline.py
register_source(MyCustomSource())
```

## Running Tests

```bash
# Run all tests
pytest

# Run with coverage
pytest --cov=. --cov-report=html

# Run specific test file
pytest tests/test_email_extractor.py -v
```

## Configuration Options (.env)

```bash
# Rate limiting
MAX_REQUESTS_PER_MINUTE=30
MAX_CONCURRENT_REQUESTS=5
MIN_DELAY_SECONDS=1.0
MAX_DELAY_SECONDS=3.0

# Proxy (optional)
HTTP_PROXY=http://proxy:8080
HTTPS_PROXY=http://proxy:8080

# Browser
USE_HEADLESS=true
BROWSER_TIMEOUT=30000

# Behavior
RESPECT_ROBOTS_TXT=true
MAX_RETRIES=3
```

## Legal Notice

This tool is for educational purposes. Always:

- Respect robots.txt
- Follow websites' Terms of Service
- Use reasonable rate limits
- Don't scrape personal data without consent
- Check local laws regarding web scraping

## License

MIT License
