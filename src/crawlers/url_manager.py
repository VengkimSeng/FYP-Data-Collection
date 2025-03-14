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
        
        # Load categories from project root config file
        config_path = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), 
                                 "config", "categories.json")
        try:
            with open(config_path, 'r', encoding='utf-8') as f:
                self.category_sources = json.load(f)
        except Exception as e:
            logger.error(f"Error loading categories config: {e}")
            self.category_sources = {}
            
        logger.info(f"URL Manager initialized for {crawler_name} with {len(self.category_sources)} categories")

    def add_urls(self, category: str, urls: Set[str], source_url: str = None) -> int:
        """Add new URLs to category file, preserving existing ones."""
        if not urls:
            return 0

        output_file = os.path.join(self.output_dir, f"{category}.json")
        existing_data = {
            "category": category,
            "sources": self.category_sources.get(category, {}),
            "crawler": self.crawler_name,
            "urls": []
        }

        # Load existing data if file exists
        if os.path.exists(output_file):
            try:
                with open(output_file, 'r', encoding='utf-8') as f:
                    existing_data = json.load(f)
            except json.JSONDecodeError:
                logger.warning(f"Could not parse existing URLs from {output_file}")
            except Exception as e:
                logger.error(f"Error reading {output_file}: {e}")

        # Convert existing URLs to set for deduplication
        existing_urls = set(existing_data["urls"])
        
        # Add new URLs
        all_urls = existing_urls.union(urls)
        
        # Update data structure
        existing_data["urls"] = sorted(list(all_urls))
        
        # Save updated data
        os.makedirs(os.path.dirname(output_file), exist_ok=True)
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(existing_data, f, indent=2, ensure_ascii=False)

        # Return number of new URLs added
        return len(all_urls) - len(existing_urls)

    def get_sources_for_category(self, category: str, source: str = None) -> List[str]:
        """Get source URLs for a category, optionally filtered by source name."""
        if category not in self.category_sources:
            return []
            
        category_data = self.category_sources[category]
        
        # Handle both list and dict formats
        if isinstance(category_data, list):
            if source:
                # For list format, return all URLs when source matches crawler name
                return category_data if source.lower() in [url.split('/')[2].replace('www.', '') for url in category_data] else []
            return category_data
            
        # Handle dictionary format
        if source:
            source_urls = category_data.get(source, [])
            return [source_urls] if isinstance(source_urls, str) else source_urls
            
        # Flatten all sources for dictionary format
        sources = []
        for src_urls in category_data.values():
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
                "sources": self.category_sources.get(category, {}),
                "crawler": self.crawler_name,
                "urls": sorted(list(self.category_urls.get(category, set())))
            }
            with open(output_file, "w", encoding="utf-8") as f:
                json.dump(url_data, f, ensure_ascii=False, indent=2)
            logger.info(f"Saved {len(self.category_urls.get(category, set()))} URLs to {output_file}")
        except Exception as e:
            logger.error(f"Error saving to {output_file}: {e}")

    def save_final_results(self) -> Dict[str, int]:
        """Save all categories one final time."""
        results = {}
        for category in self.category_urls:
            self._save_category(category)
            results[category] = len(self.category_urls[category])
        return results
