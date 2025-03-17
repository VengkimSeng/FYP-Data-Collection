"""
Incremental URL Saver Module

This module provides functionality for incrementally saving URLs as they're discovered,
with support for backup, thread safety, and progress tracking.
"""

import os
import json
import time
import threading
import logging
from typing import Set, List, Dict, Optional, Any
import traceback
from urllib.parse import urlparse

class IncrementalURLSaver:
    """
    Saves URLs incrementally to files, keeping track of what has already been saved.
    
    This class provides functionality to:
    1. Add new URLs to a category
    2. Save URLs to disk
    3. Track uniqueness of URLs
    4. Periodically back up the URLs
    """
    
    def __init__(self, output_dir: str, site_name: str, backup_interval: int = 20, 
                logger=None, force_sync: bool = True):
        """
        Initialize the saver.
        
        Args:
            output_dir: Directory to save files to
            site_name: Name of the site (used for tracking)
            backup_interval: How often to save to disk (in terms of # of new URLs)
            logger: Logger instance to use
            force_sync: Whether to force disk syncing after writes
        """
        self.output_dir = output_dir
        self.site_name = site_name
        self.backup_interval = backup_interval
        self.logger = logger or logging.getLogger(__name__)
        self.force_sync = force_sync
        
        # Create output directory if it doesn't exist
        os.makedirs(output_dir, exist_ok=True)
        
        # Create a temp directory for backups
        self.temp_dir = os.path.join(output_dir, "temp")
        os.makedirs(self.temp_dir, exist_ok=True)
        
        # Dictionary to track URLs by category and uniqueness
        self.urls_by_category = {}
        self.added_since_backup = {}
        self.backups_created = {}
        
        # Load existing URLs from files
        self._load_existing_urls()
    
    def _load_existing_urls(self):
        """Load existing URLs from JSON files."""
        try:
            # First, identify all JSON files in the output directory
            files = [f for f in os.listdir(self.output_dir) 
                    if f.endswith('.json') and os.path.isfile(os.path.join(self.output_dir, f))]
            
            self.logger.debug(f"Found {len(files)} JSON files in {self.output_dir}")
            
            # Process each file
            for filename in files:
                try:
                    # Extract category name from filename (e.g., "sport.json" -> "sport")
                    category = filename.replace('.json', '')
                    
                    file_path = os.path.join(self.output_dir, filename)
                    with open(file_path, 'r', encoding='utf-8') as f:
                        urls = json.load(f)
                        
                    if category not in self.urls_by_category:
                        self.urls_by_category[category] = set()
                        self.added_since_backup[category] = 0
                        self.backups_created[category] = 0
                    
                    self.urls_by_category[category].update(urls)
                    self.logger.debug(f"Loaded {len(urls)} URLs from {filename}")
                    
                except Exception as e:
                    self.logger.error(f"Error loading URLs from {filename}: {e}")
        except Exception as e:
            self.logger.error(f"Error during initial URL loading: {e}")
    
    def get_url_count(self, category: str) -> int:
        """Get the number of URLs for a category."""
        if category not in self.urls_by_category:
            return 0
        return len(self.urls_by_category[category])
    
    def add_urls(self, category: str, urls: List[str], save_immediately: bool = False) -> int:
        """
        Add new URLs to a category and optionally save to disk.
        
        Args:
            category: Category to add URLs to
            urls: List of URLs to add
            save_immediately: Whether to save to disk immediately
            
        Returns:
            Number of new URLs added
        """
        if not urls:
            return 0
            
        # Create category entry if it doesn't exist
        if category not in self.urls_by_category:
            self.urls_by_category[category] = set()
            self.added_since_backup[category] = 0
            self.backups_created[category] = 0
            
        # Track uniqueness
        old_count = len(self.urls_by_category[category])
        self.urls_by_category[category].update(urls)
        new_count = len(self.urls_by_category[category])
        newly_added = new_count - old_count
        
        self.added_since_backup[category] += newly_added
        
        # Save if we've added enough new URLs or if requested
        if save_immediately or self.added_since_backup[category] >= self.backup_interval:
            self.save_to_file(category)
            
        return newly_added
    
    def save_to_file(self, category: str) -> bool:
        """
        Save URLs for a category to disk.
        
        Args:
            category: Category to save
            
        Returns:
            True if successful, False otherwise
        """
        if category not in self.urls_by_category:
            self.logger.warning(f"No URLs to save for category: {category}")
            return False
            
        try:
            # Reset the added since backup counter
            self.added_since_backup[category] = 0
            self.backups_created[category] += 1
            
            # Convert set to list for serialization
            urls_list = list(self.urls_by_category[category])
            self.logger.info(f"Preparing to save {len(urls_list)} URLs for {category}")
            
            # Debug: check the existing file
            main_path = os.path.join(self.output_dir, f"{category}.json")
            if os.path.exists(main_path):
                try:
                    with open(main_path, 'r', encoding='utf-8') as f:
                        existing_data = json.load(f)
                        self.logger.info(f"Existing file {main_path} has {len(existing_data)} URLs")
                except Exception as e:
                    self.logger.warning(f"Could not read existing file: {e}")
            
            # Merge URLs and remove duplicates
            all_urls = list(set(existing_data + urls_list)) if existing_data else urls_list
            
            # First write to a temp file to avoid data loss if writing fails
            timestamp = int(time.time())
            temp_filename = f"{category}_{timestamp}.json.tmp"
            temp_path = os.path.join(self.temp_dir, temp_filename)
            
            self.logger.info(f"Writing to temp file: {temp_path}")
            with open(temp_path, 'w', encoding='utf-8') as f:
                json.dump(all_urls, f, indent=2, ensure_ascii=False)
                if self.force_sync:
                    f.flush()
                    os.fsync(f.fileno())
            
            self.logger.info(f"Temp file written successfully, moving to final location: {main_path}")
            
            # Now move the temp file to the main file
            import shutil
            shutil.move(temp_path, main_path)
            
            # Verify the file was created
            if os.path.exists(main_path):
                file_size = os.path.getsize(main_path)
                self.logger.info(f"File saved successfully: {main_path} (size: {file_size} bytes)")
            else:
                self.logger.error(f"File does not exist after save operation: {main_path}")
            
            return True
            
        except Exception as e:
            self.logger.error(f"Error saving URLs for {category}: {e}")
            self.logger.error(f"Stack trace: {traceback.format_exc()}")
            return False
    
    def save_all_categories(self) -> Dict[str, bool]:
        """
        Save all categories to disk.
        
        Returns:
            Dictionary mapping category names to success/failure status
        """
        results = {}
        for category in self.urls_by_category.keys():
            results[category] = self.save_to_file(category)
        return results

    def get_file_path(self, category: str) -> str:
        """Get the file path for a category."""
        return os.path.join(self.output_dir, f"{category}.json")
