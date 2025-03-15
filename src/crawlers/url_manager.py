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
        existing_urls = []

        # Load existing data if file exists
        if os.path.exists(output_file):
            try:
                with open(output_file, 'r', encoding='utf-8') as f:
                    existing_urls = json.load(f)
            except json.JSONDecodeError:
                logger.warning(f"Could not parse existing URLs from {output_file}")
            except Exception as e:
                logger.error(f"Error reading {output_file}: {e}")

        # Convert to sets for deduplication
        existing_urls_set = set(existing_urls)
        new_urls_set = set(urls)
        
        # Combine URLs and sort for consistent output
        all_urls = sorted(list(existing_urls_set | new_urls_set))
        
        # Save updated URLs as a simple list
        os.makedirs(os.path.dirname(output_file), exist_ok=True)
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(all_urls, f, indent=2, ensure_ascii=False)

        # Return number of new URLs added
        return len(all_urls) - len(existing_urls_set)

    def get_sources_for_category(self, category: str, source: str = None) -> List[str]:
        """Get source URLs for a category, optionally filtered by source name."""
        if category not in self.category_sources:
            return []
            
        category_data = self.category_sources[category]
        
        # Debug logging to understand the data structure
        logger.debug(f"Category data structure for {category}: {type(category_data)}")
        
        # Handle different data structures safely
        try:
            # List format: [url1, url2, ...]
            if isinstance(category_data, list):
                if source:
                    # Filter list URLs by domain containing source name
                    source_lower = source.lower().replace('crawler', '')
                    filtered_urls = []
                    for url in category_data:
                        if isinstance(url, str) and source_lower in url.lower():
                            logger.debug(f"Found matching URL for {source} in {category}: {url}")
                            filtered_urls.append(url)
                    return filtered_urls
                return category_data
            
            # Dict format: {"source1": [url1, url2], "source2": url3}
            elif isinstance(category_data, dict):
                if source:
                    # Try exact key match first
                    if source in category_data:
                        source_urls = category_data[source]
                        urls = [source_urls] if isinstance(source_urls, str) else source_urls
                        logger.debug(f"Found exact match for {source} in {category}: {urls}")
                        return urls
                    
                    # Try partial key match next (e.g., "rfa" matches "rfanews")
                    source_lower = source.lower().replace('crawler', '')
                    for key in category_data.keys():
                        if source_lower in key.lower():
                            source_urls = category_data[key]
                            urls = [source_urls] if isinstance(source_urls, str) else source_urls
                            logger.debug(f"Found partial match for {source} in key {key}: {urls}")
                            return urls
                    
                    # No matches found
                    logger.debug(f"No matching sources found for {source} in {category}")
                    return []
                
                # No source specified, return all URLs
                sources = []
                for src_urls in category_data.values():
                    if isinstance(src_urls, list):
                        sources.extend(src_urls)
                    else:
                        sources.append(src_urls)
                return sources
                
            else:
                # Unexpected data type, return empty list
                logger.warning(f"Unexpected category data type: {type(category_data)}")
                return []
                
        except Exception as e:
            logger.error(f"Error getting sources for {category}/{source}: {e}")
            return []

    def get_category_urls(self, category: str) -> List[str]:
        """Get current URLs for a category."""
        output_file = os.path.join(self.output_dir, f"{category}.json")
        urls = []
        
        # Load existing data if file exists
        if os.path.exists(output_file):
            try:
                with open(output_file, 'r', encoding='utf-8') as f:
                    urls = json.load(f)
            except Exception as e:
                logger.error(f"Error reading {output_file}: {e}")
                
        return urls

    def _save_category(self, category: str) -> None:
        """Save category URLs to file with simple list format."""
        output_file = os.path.join(self.output_dir, f"{category}.json")
        try:
            # Save as a simple sorted list
            urls_list = sorted(list(self.category_urls.get(category, set())))
            with open(output_file, "w", encoding="utf-8") as f:
                json.dump(urls_list, f, ensure_ascii=False, indent=2)
            logger.info(f"Saved {len(urls_list)} URLs to {output_file}")
        except Exception as e:
            logger.error(f"Error saving to {output_file}: {e}")

    def save_final_results(self) -> Dict[str, int]:
        """Save all categories one final time."""
        results = {}
        for category in self.category_urls:
            self._save_category(category)
            results[category] = len(self.category_urls[category])
        return results
