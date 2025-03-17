"""
Configuration settings for the article extractor.
"""

import os
import sys
from pathlib import Path

# Base directories
ROOT_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
LOG_DIR = os.path.join(ROOT_DIR, "logs", "extractors")
CHECKPOINT_DIR = os.path.join(ROOT_DIR, "output", "checkpoints")

# Checkpoint file
CHECKPOINT_FILE = os.path.join(CHECKPOINT_DIR, "extractor_checkpoint.json")

# Extractor settings
MAX_RETRIES = 3
MAX_WAIT_TIME = 30  # seconds

# Create necessary directories
os.makedirs(LOG_DIR, exist_ok=True)
os.makedirs(CHECKPOINT_DIR, exist_ok=True)

# Scraper configuration
SCRAPER_MAP = {
    "btv.com.kh": "btv_scraper",
    "www.btv.com.kh": "btv_scraper",
    "postkhmer.com": "postkhmer_scraper",
    "www.postkhmer.com": "postkhmer_scraper",
    "rfa.org": "rfa_scraper",
    "www.rfa.org": "rfa_scraper",
    "dap-news.com": "dapnews_scraper",
    "www.dap-news.com": "dapnews_scraper",
    "news.sabay.com.kh": "sabay_scraper",
    "kohsantepheapdaily.com.kh": "kohsantepheap_scraper",
    "www.kohsantepheapdaily.com.kh": "kohsantepheap_scraper"
}

# Register functions to SCRAPER_MAP should be done by individual scrapers
