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
        
        # Load category sources from config file
        config_path = os.path.join(os.path.dirname(__file__), "../config/sources.json")
        try:
            with open(config_path, 'r', encoding='utf-8') as f:
                self.category_sources = json.load(f)
        except Exception as e:
            logger.error(f"Error loading sources config: {e}")
            self.category_sources = {}
            
        logger.info(f"URL Manager initialized for {crawler_name} with {len(self.category_sources)} categories")

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

    def get_sources_for_category(self, category: str, source: str = None) -> List[str]:
        """Get source URLs for a category, optionally filtered by source name."""
        if category not in self.category_sources:
            return []
            
        if source:
            source_urls = self.category_sources[category].get(source, [])
            return [source_urls] if isinstance(source_urls, str) else source_urls
            
        # Flatten all sources for the category
        sources = []
        for src_urls in self.category_sources[category].values():
            if isinstance(src_urls, list):
                sources.extend(src_urls)
            else:
                sources.append(src_urls)
        return sources

    def _save_category(self, category: str) -> None:
        """Save category URLs to file with source information."""
        output_file = os.path.join(self.output_dir, f"{category}.json")
        try:
            url_data = {
                "category": category,
                "sources": self.category_sources[category],
                "crawler": self.crawler_name,
                "urls": sorted(list(self.category_urls[category]))
            }
            with open(output_file, "w", encoding="utf-8") as f:
                json.dump(url_data, f, ensure_ascii=False, indent=4)
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
