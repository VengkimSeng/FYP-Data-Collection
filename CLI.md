# Interactive CLI Documentation

This document provides detailed instructions for using the interactive CLI tool (`Data_Collection_CLI.py`) for Khmer News Article collection.

## Table of Contents

- [Overview](#overview)
- [Getting Started](#getting-started)
- [Main Menu Options](#main-menu-options)
- [Process Control](#process-control)
- [Configuration Management](#configuration-management)
- [Category Selection](#category-selection)
- [Command-line Arguments](#command-line-arguments)
- [Troubleshooting](#troubleshooting)

## Overview

The Data Collection CLI tool provides an interactive terminal interface for controlling the entire data collection process, from URL crawling to content extraction. It's designed to be easy to use while offering powerful control options.

Key benefits:

- Interactive numbered menus
- Real-time process monitoring
- Graceful termination capability
- Resume from interruption
- Per-category processing
- Persistent configuration settings

## Getting Started

To start the CLI tool, run:

```bash
python Data_Collection_CLI.py
```

This will display the main menu with options for different operations. The current configuration will be shown at the bottom of the menu.

## Main Menu Options

The main menu offers the following options:

### 1. Run Full Workflow (crawl + extract)

This option executes the complete data collection pipeline:

1. Synchronizes folders based on categories
2. Crawls websites to collect article URLs
3. Extracts content from those URLs

When selected, you'll be prompted to choose which categories to process (or all of them).

### 2. Crawl URLs Only

This option only performs the URL collection phase. It's useful when you:

- Need to refresh your URL database
- Want to add more URLs to existing categories
- Are testing URL collection independently

### 3. Extract Content Only

This option only performs the content extraction phase. Use this when:

- You've already collected URLs
- Need to re-extract content with different settings
- Are testing extraction independently

### 4. Resume From Interrupted Workflow

This option allows you to continue a previously interrupted process:

- **Resume Crawling**: Continues URL collection from where it stopped
- **Resume Extraction**: Continues processing URLs from the last checkpoint
- **Resume Full Workflow**: Continues the complete workflow

This is especially useful for long-running processes that were terminated.

### 5. Test Crawlers

This option launches the test mode for crawlers, allowing you to verify that individual crawlers are working correctly. You'll be guided through an interactive process to select which crawler and category to test.

### 6. Sync Folders

This option updates the folder structure to match the categories defined in your configuration file. Use this when you've added or removed categories.

### 7. Configure Settings

Opens the settings menu where you can adjust:

- URLs per category: How many URLs to target per category
- Crawl workers: Number of concurrent crawlers
- Extract workers: Number of concurrent extraction processes
- Output directory: Where to save extracted articles
- URLs directory: Where to save collected URLs
- Categories file path: Location of the categories configuration file

## Process Control

### Stopping a Running Process

You can stop any running process by pressing **Ctrl+C**. The system will:

1. Detect the interrupt signal
2. Set a stop flag
3. Try to gracefully terminate the running process
4. Inform you that you can resume later

Example message:
