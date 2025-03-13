import os
import json
import logging
from typing import Dict, Set, List, Iterable, Any

logger = logging.getLogger(__name__)

class URLManager:
    def __init__(self, output_dir: str, crawler_name: str):
        self.output_dir = output_dir
        self.crawler_name = crawler_name
        self.category_urls: Dict[str, Set[str]] = {}
        os.makedirs(output_dir, exist_ok=True)
        logger.info(f"URL Manager initialized for {crawler_name} (output: {output_dir})")

    def add_urls(self, category: str, urls: Iterable[str]) -> int:
        """Add URLs and save them directly to the output file."""
        if category not in self.category_urls:
            self.category_urls[category] = set()
        
        previous_count = len(self.category_urls[category])
        self.category_urls[category].update(urls)
        current_count = len(self.category_urls[category])
        
        # Save directly to file
        self._save_category(category)
        
        return current_count - previous_count

    def _save_category(self, category: str) -> None:
        """Save category URLs to file."""
        output_file = os.path.join(self.output_dir, f"{category}.json")
        try:
            with open(output_file, "w", encoding="utf-8") as f:
                json.dump(list(self.category_urls[category]), f, ensure_ascii=False, indent=4)
            logger.info(f"Saved {len(self.category_urls[category])} URLs to {output_file}")
        except Exception as e:
            logger.error(f"Error saving to {output_file}: {e}")

    def save_final_results(self) -> Dict[str, int]:
        """Save all categories one final time."""
        results = {}
        for category in self.category_urls:
            self._save_category(category)
            results[category] = len(self.category_urls[category])
        return results
