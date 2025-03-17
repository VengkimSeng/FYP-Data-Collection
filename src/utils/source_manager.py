"""
Source Manager

This module provides functions for loading and retrieving source URLs for crawlers.
It serves as a replacement for the URL manager source loading functionality.
"""

import os
import json
import logging
from typing import Dict, List, Optional, Set

class SourceManager:
    """
    Manages source URLs for crawlers.
    """
    
    def __init__(self, config_dir: str = "config", logger=None):
        """
        Initialize the source manager.
        
        Args:
            config_dir: Directory containing configuration files
            logger: Logger instance
        """
        self.config_dir = config_dir
        self.logger = logger or logging.getLogger(__name__)
        self.categories = {}
        self.sources = {}
        
        # Load configuration files
        self._load_categories()
        self._load_sources()
    
    def _load_categories(self) -> None:
        """Load category configuration."""
        try:
            categories_path = os.path.join(self.config_dir, "categories.json")
            if not os.path.exists(categories_path):
                self.logger.warning(f"Categories file not found: {categories_path}")
                return
                
            with open(categories_path, 'r', encoding='utf-8') as f:
                self.categories = json.load(f)
                self.logger.debug(f"Loaded {len(self.categories)} categories")
        except Exception as e:
            self.logger.error(f"Error loading categories: {e}")
    
    def _load_sources(self) -> None:
        """Load source configuration."""
        try:
            sources_path = os.path.join(self.config_dir, "sources.json")
            if not os.path.exists(sources_path):
                self.logger.warning(f"Sources file not found: {sources_path}")
                return
                
            with open(sources_path, 'r', encoding='utf-8') as f:
                self.sources = json.load(f)
                self.logger.debug(f"Loaded source configuration with {len(self.sources)} items")
        except Exception as e:
            self.logger.error(f"Error loading sources: {e}")
    
    def get_categories(self) -> List[str]:
        """Get all available categories."""
        return list(self.categories.keys())
    
    def get_site_categories(self, site_name: str) -> List[str]:
        """
        Get categories that have sources for a specific site.
        
        Args:
            site_name: Site name to filter by
            
        Returns:
            List of category names
        """
        result = []
        for category, sites in self.categories.items():
            if site_name in sites:
                result.append(category)
        return result
    
    def get_source_urls(self, category: str, site_name: str) -> List[str]:
        """
        Get source URLs for a specific category and site.
        
        Args:
            category: Category to get sources for
            site_name: Site name to filter by
            
        Returns:
            List of source URLs
        """
        # Check if the category exists in the configuration
        if category not in self.categories:
            self.logger.warning(f"Category not found: {category}")
            return []
            
        # Check if the site exists for this category
        if site_name not in self.categories[category]:
            self.logger.warning(f"No {site_name} sources for category: {category}")
            return []
            
        # Get source configuration
        source_keys = self.categories[category].get(site_name, [])
        if not source_keys:
            self.logger.warning(f"No source keys for {site_name} in {category}")
            return []
            
        # Get URLs from sources
        urls = []
        for key in source_keys:
            if key in self.sources:
                source_url = self.sources[key].get("url")
                if source_url:
                    urls.append(source_url)
        
        self.logger.debug(f"Found {len(urls)} source URLs for {site_name} - {category}")
        return urls

# Create a default instance for convenience
default_source_manager = SourceManager()

def get_source_urls(category: str, site_name: str) -> List[str]:
    """
    Get source URLs for a specific category and site using the default source manager.
    
    Args:
        category: Category to get sources for
        site_name: Site name to filter by
        
    Returns:
        List of source URLs
    """
    return default_source_manager.get_source_urls(category, site_name)

def get_site_categories(site_name: str) -> List[str]:
    """
    Get categories that have sources for a specific site using the default source manager.
    
    Args:
        site_name: Site name to filter by
        
    Returns:
        List of category names
    """
    return default_source_manager.get_site_categories(site_name)
