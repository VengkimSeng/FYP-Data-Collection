# Khmer News Article Crawler System

This system crawls Khmer language news articles from multiple websites, organizes them by category, and prepares them for natural language processing tasks.

## Table of Contents

- [Overview](#overview)
- [Directory Structure](#directory-structure)
- [Installation](#installation)
- [CLI Tool](#cli-tool)
  - [Features](#features)
  - [Basic Usage](#basic-usage)
  - [Menu Options](#menu-options)
  - [Configuration](#configuration)
  - [Command-line Arguments](#command-line-arguments)
- [Advanced Usage](#advanced-usage)
  - [URL Collection](#url-collection)
  - [Content Extraction](#content-extraction)
  - [Running Individual Crawlers](#running-individual-crawlers)
- [Troubleshooting](#troubleshooting)
- [Testing crawl_urls Function](#testing-crawl_urls-function)

## Overview

The Khmer News Article Crawler System automates the collection of Khmer language news articles from various websites. It works in two phases:

1. **URL Collection**: Extracts article URLs from specified news websites by category
2. **Content Extraction**: Downloads and extracts the actual content from these URLs

The system is designed to be modular, allowing for easy addition of new news sources and customization of extraction parameters.

## Directory Structure

```
FYP-Data-Collection/
│
├── src/                    # Source code
│   ├── crawlers/           # URL crawler scripts for each website
│   ├── extractors/         # Article content extraction scripts
│   │   └── scrapers/       # Website-specific scraper implementations
│   └── utils/              # Shared utility functions
│
├── config/                 # Configuration files
│   └── categories.json     # Website categories and URLs
│
├── output/                 # Output directories
│   ├── urls/               # Collected article URLs
│   ├── articles/           # Extracted article content
│   └── logs/               # Log files
│
├── tools/                  # Scripts and tools
│   ├── cli.py              # Command-line interface
│   ├── workflow_runner.py  # Complete workflow automation
│   └── sync_categories.py  # Sync categories to directory structure
│
└── requirements.txt        # Python dependencies
```

## Installation

1. Clone the repository:

   ```bash
   git clone <repository-url>
   cd FYP-Data-Collection
   ```

2. Install the required dependencies:

   ```bash
   # For macOS
   pip3 install -r requirements.txt

   # For Windows
   pip install -r requirements.txt
   ```

3. Set up Chrome and ChromeDriver:
   - Install Google Chrome browser if not already installed
   - For macOS users:
     - Install ChromeDriver via Homebrew: `brew install --cask chromedriver`
     - Or manually place it at "/opt/homebrew/bin/Chromedriver"
   - For Windows users:
     - Download ChromeDriver from https://chromedriver.chromium.org/downloads
     - Add it to your PATH or update its path in `src/utils/chrome_setup.py`

## CLI Tool

### Features

- Collects article URLs from specified news websites
- Extracts content from collected URLs
- Organizes articles by category
- Supports multiple concurrent workers for faster processing
- Configurable via JSON files and command-line arguments

### Basic Usage

The easiest way to run the complete workflow is using the CLI:

```bash
# For macOS
python3 tools/cli.py all

# For Windows
python tools/cli.py all

# Specify output directory
python3 tools/cli.py all --output-dir output/articles/20230101  # macOS
python tools/cli.py all --output-dir output/articles/20230101   # Windows
```

The system automatically detects your operating system and uses the appropriate Python command.

### Menu Options

The CLI offers a convenient way to run the complete process or specific steps:

```bash
# Get help
python3 tools/cli.py --help   # macOS
python tools/cli.py --help    # Windows

# Run specific steps
python3 tools/cli.py sync     # macOS: Sync categories.json to output directory structure
python tools/cli.py sync      # Windows: Sync categories.json to output directory structure

python3 tools/cli.py crawl    # macOS: Collect article URLs
python tools/cli.py crawl     # Windows: Collect article URLs

python3 tools/cli.py extract  # macOS: Extract content from collected URLs
python tools/cli.py extract   # Windows: Extract content from collected URLs

python3 tools/cli.py all      # macOS: Run complete workflow
python tools/cli.py all       # Windows: Run complete workflow
```

### Configuration

All source URLs are stored in a single configuration file:

```json
// config/categories.json
{
  "sport": [
    "https://btv.com.kh/category/sport",
    "https://kohsantepheapdaily.com.kh/category/sport",
    "..."
  ],
  "technology": [
    "..."
  ],
  "..."
}
```

Edit this file to add or remove news sources and categories.

### Command-line Arguments

Common options:

- `--output-dir`: Set output directory for articles
- `--urls-per-category`: Target number of URLs per category (default: 2500)
- `--max-workers`: Maximum crawler workers (default: 3)
- `--extract-workers`: Maximum extraction workers (default: 6)
- `--reset-checkpoint`: Reset extraction checkpoint

## Advanced Usage

### URL Collection

The URL collection phase can be run independently using the master crawler controller:

```bash
# Run the master crawler to collect article URLs
python src/crawlers/master_crawler_controller.py --urls-per-category 2500 --max-workers 3
```

Options:

- `--urls-per-category`: Number of URLs to collect per category (default: 2500)
- `--max-workers`: Maximum concurrent crawlers (default: 3)
- `--resume`: Resume from a previous crawl
- `--min-urls-per-source`: Minimum URLs to try extracting from each source (default: 50)
- `--output-dir`: Where to save output files (default: "output/urls")
- `--categories-file`: Path to categories.json file (default: config/categories.json)

### Content Extraction

The content extraction phase can be run independently:

```bash
# Extract content from collected URLs
python src/extractors/article_crawler.py --input-dir output/urls --output-dir output/articles
```

Options:

- `--input-dir`: Directory containing URL JSON files (default: "output/urls")
- `--output-dir`: Directory to save extracted articles (default: "output/articles")
- `--max-workers`: Maximum number of concurrent workers (default: 6)
- `--reset-checkpoint`: Reset the checkpoint file to process all URLs
- `--verbose`: Enable verbose output

### Running Individual Crawlers

Each crawler can be run independently for testing or specific data collection:

```bash
# Example: Run the Sabay News crawler
python src/crawlers/sabaynews_crawler.py --output output/urls/sabay --categories sport technology

# Example: Run the PostKhmer crawler
python src/crawlers/postkhmer_crawler.py
```

## Troubleshooting

### Common Issues

1. **ChromeDriver Issues**:

   - Ensure you have the correct ChromeDriver version for your Chrome browser
   - Update the ChromeDriver path in the configuration

2. **Permission Errors**:

   - Ensure write permissions for output directories
   - Run with appropriate permissions (use sudo if necessary)

3. **Network Errors**:

   - Some websites may block automated access
   - Try reducing the number of concurrent workers
   - Add delays between requests

4. **Memory Issues**:
   - For large datasets, reduce the number of concurrent workers
   - Close other applications to free up memory

If issues persist, check the log files:

- `output/logs/workflow.log`: General workflow logs
- `output/logs/categories/`: Logs for each category
- `output/logs/errors/`: Error logs for each category

## Testing crawl_urls Function

To test the `crawl_urls` function, you can run the following command:

```bash
python src/tests/crawler/main_test_crawler.py --test-crawl-urls
```

This will execute the `crawl_urls` function with a specific category and verify its execution.
