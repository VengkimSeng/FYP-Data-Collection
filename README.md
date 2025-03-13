# Khmer News Article Crawler System

This system crawls Khmer language news articles from multiple websites, organizes them by category, and prepares them for natural language processing tasks.

## Table of Contents

- [Overview](#overview)
- [Installation](#installation)
- [System Components](#system-components)
- [Quick Start Guide](#quick-start-guide)
- [Detailed Usage](#detailed-usage)
  - [Using the Workflow CLI](#using-the-workflow-cli)
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

## Installation

1. Clone the repository:

   ```bash
   git clone <repository-url>
   cd FYP-improved
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
     - Add it to your PATH or update its path in `chrome_setup.py`

## System Components

- **Master Controller**: Orchestrates all crawling tasks (`master_crawler_controller.py`)
- **Individual Crawlers**: Specialized crawlers for each news website (`1- URL-improve/` directory)
- **Overall Article Crawler**: Extracts article content from URLs (`A_Overall_Article_Crawler.py`)
- **Chrome Setup**: Common browser configuration (`chrome_setup.py`)
- **Workflow CLI**: Command-line interface for the complete workflow (`run_workflow_cli.py`)

## Quick Start Guide

The easiest way to run the complete workflow is using the Workflow CLI:

```bash
# For macOS
python3 run_workflow_cli.py all

# For Windows
python run_workflow_cli.py all

# Specify output directory
python3 run_workflow_cli.py all --output-dir Articles_20230101  # macOS
python run_workflow_cli.py all --output-dir Articles_20230101   # Windows
```

The system automatically detects your operating system and uses the appropriate Python command.

## Detailed Usage

### Using the Workflow CLI

The Workflow CLI offers a convenient way to run the complete process or specific steps:

```bash
# Get help
python run_workflow_cli.py --help

# Run specific steps
python run_workflow_cli.py sync      # Sync categories.json to Scrape_urls directory
python run_workflow_cli.py crawl     # Collect article URLs
python run_workflow_cli.py extract   # Extract content from collected URLs
python run_workflow_cli.py all       # Run complete workflow
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
python master_crawler_controller.py --urls-per-category 2500 --max-workers 3
```

Options:

- `--urls-per-category`: Number of URLs to collect per category (default: 2500)
- `--max-workers`: Maximum concurrent crawlers (default: 3)
- `--resume`: Resume from a previous crawl
- `--min-urls-per-source`: Minimum URLs to try extracting from each source (default: 50)
- `--output-dir`: Where to save output files (default: "Selected_URLs")
- `--categories-file`: Path to categories.json file (default: categories.json)

### Content Extraction

The content extraction phase can be run independently:

```bash
# Extract content from collected URLs
python run_article_crawler.py --input-dir Scrape_urls --output-dir Articles
```

Options:

- `--input-dir`: Directory containing URL JSON files (default: "Scrape_urls")
- `--output-dir`: Directory to save extracted articles (default: "Article")
- `--max-workers`: Maximum number of concurrent workers (default: 6)
- `--reset-checkpoint`: Reset the checkpoint file to process all URLs
- `--verbose`: Enable verbose output

### Running Individual Crawlers

Each crawler can be run independently for testing or specific data collection:

```bash
# Example: Run the Sabay News crawler
python "1- URL-improve/sabaynews_crawler.py" --output sabay_articles --categories sport technology

# Example: Run the PostKhmer crawler
python "1- URL-improve/postkhmer_crawler.py"
```

## Configuration

All source URLs are stored in a single configuration file:

```json
// categories.json
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

- `workflow.log`: General workflow logs
- `Category_Logs/`: Logs for each category
- `Category_Errors/`: Error logs for each category
