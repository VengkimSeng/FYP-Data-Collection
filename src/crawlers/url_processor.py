"""
URL Processor - Functions for processing, filtering, and saving URLs

This module provides utilities for URL manipulation, filtering,
and storage specific to the crawler system.
"""

import os
import json
import random
import logging
from typing import Dict, List, Set
from urllib.parse import urlparse

logger = logging.getLogger(__name__)

# Domain-specific URL patterns for filtering
DOMAIN_PATTERNS = {
    "btv.com.kh": "/article/",
    "rfa.org": ["/news/", ".html"],
    "postkhmer.com": ["/politics/", "/business/", "/financial/", "/sport/"],
    "dap-news.com": ["/economic/", "/sport/", "/politic/", "/technology/", "/health/"],
    "kohsantepheapdaily.com.kh": ["/article/", ".html"],
    "news.sabay.com.kh": "/article/"
}

def filter_article_urls(urls: List[str], domain: str) -> List[str]:
    """Filter URLs to ensure they are valid article URLs."""
    filtered = []
    patterns = DOMAIN_PATTERNS.get(domain, ["/article/", "/news/", ".html", "/detail/", "/story/"])
    patterns = patterns if isinstance(patterns, list) else [patterns]
    
    for url in urls:
        if url and isinstance(url, str) and any(pattern in url for pattern in patterns):
            filtered.append(url)
            
    logger.debug(f"Filtered {len(filtered)} article URLs from {len(urls)} for {domain}")
    return filtered

def save_urls_to_file(urls: List[str], output_path: str, format_type: str = "json") -> bool:
    """Save URLs to a file in the specified format."""
    try:
        os.makedirs(os.path.dirname(output_path) or ".", exist_ok=True)
        unique_urls = list(set(urls))
        
        if format_type.lower() == "json":
            with open(output_path, "w", encoding="utf-8") as f:
                json.dump(unique_urls, f, ensure_ascii=False, indent=2)
        else:
            with open(output_path, "w", encoding="utf-8") as f:
                for url in unique_urls:
                    f.write(f"{url}\n")
                    
        logger.info(f"Saved {len(unique_urls)} URLs to {output_path}")
        return True
    except Exception as e:
        logger.error(f"Error saving URLs to {output_path}: {e}")
        return False

def select_random_urls(urls: List[str], count: int) -> List[str]:
    """Select a random subset of URLs."""
    return random.sample(urls, count) if len(urls) > count else urls

def collect_urls_from_dir(directory: str, category: str = None) -> Set[str]:
    """Collect URLs from all files in a directory."""
    urls = set()
    if not os.path.exists(directory):
        return urls
        
    for root, _, files in os.walk(directory):
        for file in files:
            if file.endswith((".json", ".txt")) and (not category or category in file):
                try:
                    urls.update(_read_urls_from_file(os.path.join(root, file)))
                except Exception as e:
                    logger.warning(f"Error reading {file}: {e}")
    return urls

def _read_urls_from_file(filepath: str) -> Set[str]:
    """Read URLs from a file (helper function)."""
    urls = set()
    with open(filepath, "r", encoding="utf-8") as f:
        if filepath.endswith(".json"):
            data = json.load(f)
            if isinstance(data, dict) and "unique_urls" in data:
                urls.update(url for url in data["unique_urls"] if url)
            else:
                urls.update(url for url in data if url)
        else:
            urls.update(line.strip() for line in f if line.strip())
    return urls
