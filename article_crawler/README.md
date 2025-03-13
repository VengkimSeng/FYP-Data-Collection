# Article Crawler

A modular article content extraction system for Khmer news websites.

## Overview

This package provides a framework for extracting article content from various Khmer news websites and saving them in a structured format. It supports multiple websites through specialized scrapers and provides concurrent processing for efficiency.

## Features

- Modular design with specialized scrapers for each website
- Concurrent processing with multiple threads
- Checkpoint system to avoid re-scraping already processed URLs
- Detailed logging and error tracking
- Customizable output formats and directories

## Supported Websites

- BTV (btv.com.kh)
- Post Khmer (postkhmer.com)
- Radio Free Asia (rfa.org)
- DAP News (dap-news.com)
- Sabay News (news.sabay.com.kh)
- Kohsantepheapdaily (kohsantepheapdaily.com.kh)

## Usage

Basic usage:

```bash
python -m article_crawler --input-dir "Scrape_urls" --output-dir "Articles"
```

### Command-Line Options

- `--input-dir`: Directory containing URL JSON files (default: "Scrape_urls")
- `--output-dir`: Directory to save extracted articles (default: "Article")
- `--max-workers`: Maximum number of concurrent workers (default: 6)
- `--reset-checkpoint`: Reset the checkpoint file to process all URLs
- `--verbose`: Enable verbose output

## Adding New Scrapers

To add support for a new website:

1. Create a new file in the `scrapers` directory (e.g., `my_site_scraper.py`)
2. Define a scraper function that accepts `url` and `category` parameters
3. Register the scraper in `SCRAPER_MAP` with the website's base URL as the key
4. Import the scraper in `scrapers/__init__.py`

Example:

```python
from ..scrapers.generic_scraper import generic_scrape
from ..config import SCRAPER_MAP

def scrape_my_site(url, category):
    """Scrape articles from My Site."""
    return generic_scrape(url, category, "h1.title", "div.content")

# Register the scraper
SCRAPER_MAP["https://mysite.example.com"] = scrape_my_site
```

## Directory Structure

- `main.py`: Main entry point
- `config.py`: Configuration settings
- `logger.py`: Logging utilities
- `utils.py`: General utility functions
- `storage.py`: File handling for saving article data
- `browser.py`: Browser utilities
- `file_processor.py`: URL file processing
- `url_processor.py`: Individual URL processing
- `scrapers/`: Directory containing website-specific scrapers
