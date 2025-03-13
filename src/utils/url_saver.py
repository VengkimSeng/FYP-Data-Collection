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
            self.logger.info(f"Saved {len(final_urls)} URLs to final file for category '{category}'")
        return results
    
    def _save_urls_to_file(self, urls: Iterable[str], file_path: str, 
                          format_type: str = "json", ensure_ascii: bool = False, 
                          indent: int = 4) -> bool:
        try:
            urls_list = sorted(list(set(urls)))
            if format_type.lower() == "json":
                with open(file_path, 'w', encoding='utf-8') as f:
                    json.dump(urls_list, f, ensure_ascii=ensure_ascii, indent=indent)
            else:
                with open(file_path, 'w', encoding='utf-8') as f:
                    for url in urls_list:
                        f.write(f"{url}\n")
            return True
        except Exception as e:
            self.logger.error(f"Error saving URLs to file {file_path}: {str(e)}")
            return False
    
    def _load_urls_from_file(self, file_path: str) -> List[str]:
        try:
            if file_path.endswith('.json'):
                with open(file_path, 'r', encoding='utf-8') as f:
                    return json.load(f)
            else:
                with open(file_path, 'r', encoding='utf-8') as f:
                    return [line.strip() for line in f if line.strip()]
        except Exception as e:
            self.logger.error(f"Error loading URLs from file {file_path}: {str(e)}")
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
