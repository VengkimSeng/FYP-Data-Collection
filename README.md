# Khmer News Article Crawler System

This system crawls Khmer language news articles from multiple websites, organizes them by category, and prepares them for natural language processing tasks.

## Table of Contents

- [Overview](#overview)
- [Directory Structure](#directory-structure)
- [Installation](#installation)
- [Quick Start Guide](#quick-start-guide)
- [Detailed Usage](#detailed-usage)
  - [Using the CLI](#using-the-cli)
  - [URL Collection](#url-collection)
  - [Content Extraction](#content-extraction)
  - [Running Individual Crawlers](#running-individual-crawlers)
- [Configuration](#configuration)
- [Troubleshooting](#troubleshooting)

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

## Quick Start Guide

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

## Detailed Usage

### Using the CLI

The CLI offers a convenient way to run the complete process or specific steps:

```bash
# Get help
python tools/cli.py --help

# Run specific steps
python tools/cli.py sync      # Sync categories.json to output directory structure
python tools/cli.py crawl     # Collect article URLs
python tools/cli.py extract   # Extract content from collected URLs
python tools/cli.py all       # Run complete workflow
```

Common options:

- `--output-dir`: Set output directory for articles
- `--urls-per-category`: Target number of URLs per category (default: 2500)
- `--max-workers`: Maximum crawler workers (default: 3)
- `--extract-workers`: Maximum extraction workers (default: 6)
- `--reset-checkpoint`: Reset extraction checkpoint

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

## Configuration

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
