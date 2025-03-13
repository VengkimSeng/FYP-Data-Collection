#!/usr/bin/env python3
"""
Run Article Crawler

This script provides a simple way to run the article crawler from the command line.
It handles importing the appropriate modules and passing command-line arguments.

Usage:
    python run_article_crawler.py [--input-dir DIRECTORY] [--output-dir DIRECTORY] [--reset-checkpoint]
"""

import sys
from article_crawler.main import main

if __name__ == "__main__":
    sys.exit(main())
