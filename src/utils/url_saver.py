import os
import json
import logging
import time
import threading
from typing import Set, Dict, List, Iterable, Union, Optional

class URLSaver:
    def __init__(self, output_dir: str, crawler_name: str):
        self.output_dir = output_dir
        self.crawler_name = crawler_name
        self.lock = threading.Lock()
        self.logger = logging.getLogger(f"{crawler_name}_url_saver")
        
        self.temp_dir = os.path.join(output_dir, "temp", f"{int(time.time())}_{crawler_name}")
        os.makedirs(self.temp_dir, exist_ok=True)
        os.makedirs(output_dir, exist_ok=True)
        
        self.category_urls: Dict[str, Set[str]] = {}
    
    def add_urls(self, category: str, urls: Iterable[str]) -> None:
        with self.lock:
            if category not in self.category_urls:
                self.category_urls[category] = set()
            self.category_urls[category].update(urls)
            self._save_temp_file(category, urls)
    
    def _save_temp_file(self, category: str, urls: Iterable[str]) -> None:
        temp_file = os.path.join(self.temp_dir, f"{category}_urls.json")
        self._save_urls_to_file(urls, temp_file)
        self.logger.info(f"Saved {len(urls)} URLs to temporary file for category '{category}'")
    
    def save_final_results(self) -> Dict[str, int]:
        results = {}
        for category, urls in self.category_urls.items():
            output_file = os.path.join(self.output_dir, f"{category}.json")
            existing_urls = set()
            if os.path.exists(output_file):
                existing_urls = set(self._load_urls_from_file(output_file))
            final_urls = existing_urls.union(urls)
            self._save_urls_to_file(final_urls, output_file)
            results[category] = len(final_urls)
        return results
    
    def _save_urls_to_file(self, urls: Iterable[str], file_path: str, 
                          format_type: str = "json", ensure_ascii: bool = False, 
                          indent: int = 4) -> bool:
        try:
            os.makedirs(os.path.dirname(file_path), exist_ok=True)
            urls_list = sorted(list(set(urls)))
            if format_type.lower() == "json":
                with open(file_path, "w", encoding="utf-8") as f:
                    json.dump(urls_list, f, ensure_ascii=ensure_ascii, indent=indent)
            else:
                with open(file_path, "w", encoding="utf-8") as f:
                    for url in urls_list:
                        f.write(f"{url}\n")
            return True
        except Exception as e:
            self.logger.error(f"Error saving URLs to {file_path}: {e}")
            return False
    
    def _load_urls_from_file(self, file_path: str) -> List[str]:
        try:
            if file_path.endswith('.json'):
                with open(file_path, "r", encoding="utf-8") as f:
                    return json.load(f)
            else:
                with open(file_path, "r", encoding="utf-8") as f:
                    return [line.strip() for line in f if line.strip()]
        except Exception as e:
            self.logger.error(f"Error loading URLs from {file_path}: {e}")
            return []

# For testing the module directly
if __name__ == "__main__":
    # Example usage
    test_urls = {
        "sport": ["https://example.com/sports/1", "https://example.com/sports/2"],
        "economy": ["https://example.com/economy/1", "https://example.com/economy/2"]
    }
    url_saver = URLSaver(output_dir="output/urls", crawler_name="test_crawler")
    for category, urls in test_urls.items():
        url_saver.add_urls(category, urls)
    url_saver.save_final_results()
    url_saver.logger.info("Test completed")

"""
URL Saver Module

This module provides both class-based and functional interfaces for saving URLs.
"""

# Standalone functions for direct use
def save_urls_to_file(urls: Iterable[str], 
                     output_path: str, 
                     format_type: str = "json", 
                     ensure_ascii: bool = False, 
                     indent: int = 4,
                     sort_urls: bool = True) -> bool:
    """Save URLs to a file in either JSON or TXT format."""
    try:
        os.makedirs(os.path.dirname(output_path) or ".", exist_ok=True)
        unique_urls = list(set(urls))
        
        if sort_urls:
            unique_urls.sort()
            
        if format_type.lower() == "json":
            temp_file = f"{output_path}.temp"
            with open(temp_file, "w", encoding="utf-8") as f:
                json.dump(unique_urls, f, ensure_ascii=ensure_ascii, indent=indent)
            os.replace(temp_file, output_path)
        else:
            with open(output_path, "w", encoding="utf-8") as f:
                for url in unique_urls:
                    f.write(f"{url}\n")
        return True
    except Exception as e:
        logging.error(f"Error saving URLs to {output_path}: {e}")
        return False

def save_urls_to_multiple_formats(urls: Iterable[str],
                                base_path: str,
                                formats: List[str] = ["json", "txt"],
                                sort_urls: bool = True) -> Dict[str, bool]:
    """Save URLs to multiple file formats."""
    results = {}
    for fmt in formats:
        path = f"{base_path}.{fmt}"
        results[fmt] = save_urls_to_file(
            urls=urls,
            output_path=path,
            format_type=fmt,
            sort_urls=sort_urls
        )
    return results

def load_urls_from_file(file_path: str) -> List[str]:
    """Load URLs from a file (either JSON or TXT)."""
    try:
        if file_path.endswith('.json'):
            with open(file_path, "r", encoding="utf-8") as f:
                data = json.load(f)
                if isinstance(data, dict) and "unique_urls" in data:
                    return [url for url in data["unique_urls"] if url]
                return [url for url in data if url]
        else:
            with open(file_path, "r", encoding="utf-8") as f:
                return [line.strip() for line in f if line.strip()]
    except Exception as e:
        logging.error(f"Error loading URLs from {file_path}: {e}")
        return []
