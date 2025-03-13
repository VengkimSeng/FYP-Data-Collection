"""
Category Handler - Manages category-specific operations for web crawling

This module handles loading, processing, and managing category data and operations
for the crawler system.
"""

import os
import json
import random
import logging
from typing import Dict, List, Set, Optional
from urllib.parse import urlparse

from url_processor import save_urls_to_file, select_random_urls

logger = logging.getLogger(__name__)

class CategoryHandler:
    """
    Handles category-specific operations and state management.
    
    Features:
    - Category data loading and validation
    - Category progress tracking
    - URL quota management per category
    - Results saving and resumption
    """
    
    def __init__(
        self,
        output_dir: str,
        urls_per_category: int,
        min_urls_per_source: int = 50,
        allow_resume: bool = True
    ):
        """
        Initialize the category handler.
        
        Args:
            output_dir: Directory for output files
            urls_per_category: Target number of URLs per category
            min_urls_per_source: Minimum URLs to extract from each source
            allow_resume: Whether to enable resume functionality
        """
        self.output_dir = output_dir
        self.urls_per_category = urls_per_category
        self.min_urls_per_source = min_urls_per_source
        self.allow_resume = allow_resume
        
        # Create output directory
        os.makedirs(output_dir, exist_ok=True)
        
        # State tracking
        self.category_urls: Dict[str, Set[str]] = {}
        self.already_crawled: Dict[str, Set[str]] = {}
        
    def load_categories(self, categories_file: str) -> Dict[str, List[str]]:
        """
        Load and validate category data from file.
        
        Args:
            categories_file: Path to categories JSON file
            
        Returns:
            Dictionary mapping categories to source URLs
        """
        try:
            with open(categories_file, "r", encoding="utf-8") as f:
                categories = json.load(f)
            
            # Initialize storage for each category
            for category in categories:
                self.category_urls[category] = set()
            
            # Log category information
            for category, urls in categories.items():
                logger.info(f"Category '{category}': {len(urls)} URLs")
                for url in urls[:3]:
                    logger.info(f"  - {url}")
                if len(urls) > 3:
                    logger.info(f"  - ... and {len(urls) - 3} more URLs")
            
            return categories
            
        except Exception as e:
            logger.error(f"Error loading categories from {categories_file}: {e}")
            return {}
    
    def load_existing_urls(self) -> None:
        """Load existing URLs from output directory for resume functionality."""
        if not self.allow_resume:
            return
            
        logger.info("Loading existing URLs for resume")
        
        for category in self.category_urls:
            output_file = os.path.join(self.output_dir, f"{category}.json")
            if os.path.exists(output_file):
                try:
                    with open(output_file, "r", encoding="utf-8") as f:
                        existing_urls = json.load(f)
                        self.category_urls[category].update(existing_urls)
                        logger.info(f"Loaded {len(existing_urls)} existing URLs for {category}")
                except Exception as e:
                    logger.error(f"Error loading existing URLs for {category}: {e}")
    
    def needs_more_urls(self, category: str) -> bool:
        """Check if a category needs more URLs."""
        return len(self.category_urls[category]) < self.urls_per_category
    
    def add_urls(self, category: str, urls: Set[str], source_url: Optional[str] = None) -> int:
        """
        Add URLs to a category.
        
        Args:
            category: Target category
            urls: URLs to add
            source_url: Source URL these were collected from
            
        Returns:
            Number of new URLs added
        """
        if source_url:
            self.already_crawled[source_url] = urls
        
        previous_count = len(self.category_urls[category])
        self.category_urls[category].update(urls)
        new_count = len(self.category_urls[category])
        
        added_count = new_count - previous_count
        if added_count > 0:
            logger.info(f"Added {added_count} new URLs to category {category}")
            
            # Save intermediate results if we have new URLs
            self.save_intermediate_results(category)
            
        return added_count
    
    def save_intermediate_results(self, category: str) -> None:
        """Save intermediate results for a category."""
        output_file = os.path.join(self.output_dir, f"{category}_intermediate.json")
        try:
            save_urls_to_file(list(self.category_urls[category]), output_file)
            logger.debug(f"Saved intermediate results for {category}")
        except Exception as e:
            logger.error(f"Error saving intermediate results for {category}: {e}")
    
    def save_final_results(self) -> None:
        """Save final results for all categories."""
        for category, urls in self.category_urls.items():
            urls_list = list(urls)
            
            # Select random URLs if we have more than the target
            if len(urls_list) > self.urls_per_category:
                selected_urls = select_random_urls(urls_list, self.urls_per_category)
            else:
                selected_urls = urls_list
                
            # Save to final output file using url_processor
            output_file = os.path.join(self.output_dir, f"{category}.json")
            save_urls_to_file(selected_urls, output_file)
            logger.info(f"Saved {len(selected_urls)} URLs for category {category} to {output_file}")
    
    def get_urls_needed(self, category: str) -> int:
        """Get number of URLs still needed for a category."""
        return max(0, self.urls_per_category - len(self.category_urls[category]))
    
    def get_category_stats(self) -> Dict[str, Dict[str, int]]:
        """Get statistics about category progress."""
        stats = {}
        for category in self.category_urls:
            current = len(self.category_urls[category])
            stats[category] = {
                "current": current,
                "target": self.urls_per_category,
                "needed": self.get_urls_needed(category),
                "completion": (current / self.urls_per_category * 100) if self.urls_per_category > 0 else 100
            }
        return stats
    
    def has_processed_url(self, url: str) -> bool:
        """Check if a URL has been processed already."""
        return url in self.already_crawled
    
    def get_processed_urls(self, url: str) -> Set[str]:
        """Get previously processed URLs for a source URL."""
        return self.already_crawled.get(url, set())
