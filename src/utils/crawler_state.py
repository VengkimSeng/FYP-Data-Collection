"""
CrawlerState - Manages persistent state for resumable crawling

This module provides functionality to track and save crawler progress,
enabling resuming interrupted crawls and detailed reporting.
"""

import os
import json
import time
import logging
import tempfile
import shutil
from typing import Dict, List, Set, Any, Optional
from datetime import datetime
import threading
import copy
from urllib.parse import urlparse

logger = logging.getLogger(__name__)

class CrawlerState:
    """
    Maintains persistent crawler state for resumability.
    
    Features:
    - Tracks progress by category and source
    - Saves state to disk with atomic operations
    - Provides summary statistics and reporting
    - Handles state corruption recovery
    """
    
    def __init__(
        self,
        state_file: str,
        auto_save_interval: int = 60,  # In seconds
        backup_count: int = 3
    ):
        """
        Initialize the crawler state manager.
        
        Args:
            state_file: Path to the state file
            auto_save_interval: Interval in seconds for automatic state saving
            backup_count: Number of backup state files to maintain
        """
        self.state_file = state_file
        self.auto_save_interval = auto_save_interval
        self.backup_count = backup_count
        
        # Default state structure
        self.state = {
            "crawler_info": {
                "start_time": time.time(),
                "last_updated": time.time(),
                "total_runtime": 0,
                "version": "1.0",
            },
            "categories": {},
            "domains": {},
            "completed_urls": {},
            "failed_urls": {},
            "stats": {
                "urls_processed": 0,
                "urls_succeeded": 0,
                "urls_failed": 0,
                "by_category": {}
            }
        }
        
        # Lock for thread safety
        self.lock = threading.RLock()
        
        # Load existing state if available
        self._load_state()
        
        # Auto-save thread
        self._stop_auto_save = threading.Event()
        self._auto_save_thread = None
        self._start_auto_save()
        
        logger.info(f"CrawlerState initialized: {state_file}")
    
    def _start_auto_save(self):
        """Start the auto-save thread."""
        if self.auto_save_interval <= 0:
            return
            
        self._auto_save_thread = threading.Thread(
            target=self._auto_save_worker,
            daemon=True
        )
        self._auto_save_thread.start()
        logger.debug(f"Auto-save thread started (interval: {self.auto_save_interval}s)")
    
    def _auto_save_worker(self):
        """Worker thread for automatic state saving."""
        while not self._stop_auto_save.is_set():
            # Sleep for the auto-save interval
            self._stop_auto_save.wait(self.auto_save_interval)
            
            if not self._stop_auto_save.is_set():
                try:
                    self.save()
                except Exception as e:
                    logger.error(f"Error in auto-save: {e}")
    
    def _load_state(self):
        """Load state from file, handling errors and recovery."""
        # Check for main state file
        if os.path.exists(self.state_file):
            try:
                with open(self.state_file, 'r') as f:
                    loaded_state = json.load(f)
                
                # Validate state structure
                if self._validate_state(loaded_state):
                    self.state = loaded_state
                    logger.info(f"Loaded state from {self.state_file}")
                    return
                else:
                    logger.warning("State file has invalid format, trying backups")
            except Exception as e:
                logger.error(f"Error loading state from {self.state_file}: {e}")
                
        # Try loading from backups
        backup_loaded = False
        for i in range(1, self.backup_count + 1):
            backup_file = f"{self.state_file}.bak{i}"
            if os.path.exists(backup_file):
                try:
                    with open(backup_file, 'r') as f:
                        loaded_state = json.load(f)
                    
                    if self._validate_state(loaded_state):
                        self.state = loaded_state
                        logger.info(f"Loaded state from backup: {backup_file}")
                        backup_loaded = True
                        break
                except Exception:
                    continue
        
        if not backup_loaded:
            logger.info("No valid state found, starting with empty state")
    
    def _validate_state(self, state: Dict[str, Any]) -> bool:
        """
        Validate that the loaded state has the correct structure.
        
        Args:
            state: State dictionary to validate
            
        Returns:
            Whether the state is valid
        """
        required_keys = ["crawler_info", "categories", "domains", "completed_urls", "stats"]
        return all(key in state for key in required_keys)
    
    def save(self) -> bool:
        """
        Save the current state to disk using atomic operations.
        
        Returns:
            Whether the save was successful
        """
        with self.lock:
            # Update timestamps
            current_time = time.time()
            self.state["crawler_info"]["last_updated"] = current_time
            self.state["crawler_info"]["total_runtime"] = current_time - self.state["crawler_info"]["start_time"]
            
            # Create state directory if it doesn't exist
            os.makedirs(os.path.dirname(os.path.abspath(self.state_file)), exist_ok=True)
            
            # First rotate any existing backups
            self._rotate_backups()
            
            # Write to a temporary file first
            with tempfile.NamedTemporaryFile(mode='w', delete=False) as tmp:
                try:
                    # Write state to temporary file
                    json.dump(self.state, tmp, indent=2)
                    tmp.flush()
                    os.fsync(tmp.fileno())  # Ensure data is written to disk
                    
                    # Move temp file to state file (atomic operation)
                    if os.name == 'nt':  # Windows needs special handling for atomic file replacement
                        tmp.close()
                        if os.path.exists(self.state_file):
                            os.replace(tmp.name, self.state_file)
                        else:
                            shutil.move(tmp.name, self.state_file)
                    else:
                        # Unix-like systems can do atomic renames
                        shutil.move(tmp.name, self.state_file)
                        
                    logger.debug(f"State saved to {self.state_file}")
                    return True
                    
                except Exception as e:
                    logger.error(f"Error saving state: {e}")
                    
                    # Cleanup temp file on error
                    if os.path.exists(tmp.name):
                        try:
                            os.unlink(tmp.name)
                        except:
                            pass
                            
                    return False
    
    def _rotate_backups(self):
        """Rotate backup files, keeping the specified number of backups."""
        # Remove oldest backup if it exists
        oldest_backup = f"{self.state_file}.bak{self.backup_count}"
        if os.path.exists(oldest_backup):
            try:
                os.remove(oldest_backup)
            except Exception as e:
                logger.warning(f"Could not remove old backup {oldest_backup}: {e}")
        
        # Shift existing backups
        for i in range(self.backup_count - 1, 0, -1):
            src = f"{self.state_file}.bak{i}"
            dst = f"{self.state_file}.bak{i+1}"
            if os.path.exists(src):
                try:
                    shutil.move(src, dst)
                except Exception as e:
                    logger.warning(f"Could not rotate backup from {src} to {dst}: {e}")
        
        # Copy current state file to first backup
        if os.path.exists(self.state_file):
            try:
                shutil.copy2(self.state_file, f"{self.state_file}.bak1")
            except Exception as e:
                logger.warning(f"Could not create backup of current state: {e}")
    
    def _extract_domain(self, url: str) -> str:
        """Extract domain from URL."""
        try:
            return urlparse(url).netloc.lower()
        except Exception:
            return "unknown"
    
    def register_category(self, category: str, target_count: int) -> None:
        """
        Register a category to track.
        
        Args:
            category: Category name
            target_count: Target number of URLs for this category
        """
        with self.lock:
            if category not in self.state["categories"]:
                self.state["categories"][category] = {
                    "target_count": target_count,
                    "processed_count": 0,
                    "success_count": 0,
                    "failure_count": 0,
                    "sources": {},
                    "last_processed_time": None
                }
                logger.info(f"Registered category '{category}' with target count {target_count}")
            else:
                # Update target count if category already exists
                self.state["categories"][category]["target_count"] = target_count
                logger.info(f"Updated category '{category}' target count to {target_count}")
    
    def register_domain(self, domain: str) -> None:
        """
        Register a domain to track.
        
        Args:
            domain: Domain name
        """
        with self.lock:
            if domain not in self.state["domains"]:
                self.state["domains"][domain] = {
                    "first_seen": time.time(),
                    "last_accessed": time.time(),
                    "success_count": 0,
                    "failure_count": 0,
                    "total_time": 0,
                    "average_time": 0
                }
            else:
                self.state["domains"][domain]["last_accessed"] = time.time()
    
    def record_url_start(self, url: str, category: str, source_url: Optional[str] = None) -> None:
        """
        Record the start of URL processing.
        
        Args:
            url: URL being processed
            category: Category of the URL
            source_url: Source URL from which this URL was discovered
        """
        with self.lock:
            # Ensure category exists
            if category not in self.state["categories"]:
                self.register_category(category, 0)
            
            domain = self._extract_domain(url)
            self.register_domain(domain)
            
            # Record source URL if provided
            if source_url:
                source_domain = self._extract_domain(source_url)
                if source_domain not in self.state["categories"][category].get("sources", {}):
                    self.state["categories"][category]["sources"][source_domain] = {
                        "count": 0,
                        "success_count": 0,
                        "failure_count": 0
                    }
    
    def record_url_completion(
        self,
        url: str,
        category: str,
        success: bool,
        source_url: Optional[str] = None,
        duration: Optional[float] = None,
        result_data: Optional[Dict[str, Any]] = None
    ) -> None:
        """
        Record the completion of URL processing.
        
        Args:
            url: URL that was processed
            category: Category of the URL
            success: Whether processing was successful
            source_url: Source URL from which this URL was discovered
            duration: Duration of processing in seconds
            result_data: Additional data about the result
        """
        with self.lock:
            # Ensure category exists
            if category not in self.state["categories"]:
                self.register_category(category, 0)
                
            # Get the domain
            domain = self._extract_domain(url)
            self.register_domain(domain)
            
            # Update category stats
            cat_state = self.state["categories"][category]
            cat_state["processed_count"] += 1
            cat_state["last_processed_time"] = time.time()
            
            if success:
                cat_state["success_count"] += 1
                # Record successful URL
                self.state["completed_urls"][url] = {
                    "category": category,
                    "domain": domain,
                    "time": time.time(),
                    "source_url": source_url or ""
                }
                
                # Update domain stats
                dom_state = self.state["domains"][domain]
                dom_state["success_count"] += 1
                
            else:
                cat_state["failure_count"] += 1
                # Record failed URL
                self.state["failed_urls"][url] = {
                    "category": category,
                    "domain": domain,
                    "time": time.time(),
                    "source_url": source_url or "",
                    "error": result_data.get("error", "") if result_data else ""
                }
                
                # Update domain stats
                dom_state = self.state["domains"][domain]
                dom_state["failure_count"] += 1
            
            # Record source information if available
            if source_url:
                source_domain = self._extract_domain(source_url)
                if source_domain in cat_state["sources"]:
                    src_stats = cat_state["sources"][source_domain]
                    src_stats["count"] += 1
                    if success:
                        src_stats["success_count"] += 1
                    else:
                        src_stats["failure_count"] += 1
            
            # Update duration statistics if provided
            if duration is not None and duration > 0:
                dom_state = self.state["domains"][domain]
                dom_state["total_time"] += duration
                total_count = dom_state["success_count"] + dom_state["failure_count"]
                dom_state["average_time"] = dom_state["total_time"] / total_count if total_count > 0 else 0
            
            # Update overall stats
            self.state["stats"]["urls_processed"] += 1
            if success:
                self.state["stats"]["urls_succeeded"] += 1
            else:
                self.state["stats"]["urls_failed"] += 1
                
            # Update category-specific stats in overall stats
            if category not in self.state["stats"]["by_category"]:
                self.state["stats"]["by_category"][category] = {
                    "processed": 0, "succeeded": 0, "failed": 0
                }
            
            cat_stats = self.state["stats"]["by_category"][category]
            cat_stats["processed"] += 1
            if success:
                cat_stats["succeeded"] += 1
            else:
                cat_stats["failed"] += 1
    
    def has_processed_url(self, url: str) -> bool:
        """
        Check if a URL has been processed (successfully or failed).
        
        Args:
            url: URL to check
            
        Returns:
            Whether the URL has been processed
        """
        with self.lock:
            return url in self.state["completed_urls"] or url in self.state["failed_urls"]
    
    def get_category_progress(self, category: str) -> Dict[str, Any]:
        """
        Get progress information for a specific category.
        
        Args:
            category: Category to get progress for
            
        Returns:
            Dictionary with progress information
        """
        with self.lock:
            if category not in self.state["categories"]:
                return {
                    "target_count": 0,
                    "processed_count": 0,
                    "success_count": 0,
                    "failure_count": 0,
                    "completion_percentage": 0
                }
                
            cat_state = self.state["categories"][category]
            target = cat_state["target_count"]
            processed = cat_state["processed_count"]
            success = cat_state["success_count"]
            failure = cat_state["failure_count"]
            
            completion = (success / target * 100) if target > 0 else 0
            
            return {
                "target_count": target,
                "processed_count": processed,
                "success_count": success,
                "failure_count": failure,
                "completion_percentage": completion
            }
    
    def get_domain_stats(self, domain: str) -> Dict[str, Any]:
        """
        Get statistics for a specific domain.
        
        Args:
            domain: Domain to get statistics for
            
        Returns:
            Dictionary with domain statistics
        """
        with self.lock:
            if domain not in self.state["domains"]:
                return {}
                
            return copy.deepcopy(self.state["domains"][domain])
    
    def get_summary(self) -> Dict[str, Any]:
        """
        Get a summary of the crawler state.
        
        Returns:
            Dictionary with crawler state summary
        """
        with self.lock:
            # Create a copy to avoid modification during summarization
            state_copy = copy.deepcopy(self.state)
            
            # Calculate elapsed time
            start_time = state_copy["crawler_info"]["start_time"]
            current_time = time.time()
            elapsed_time = current_time - start_time
            
            # Format timestamps for readability
            start_time_str = datetime.fromtimestamp(start_time).strftime("%Y-%m-%d %H:%M:%S")
            
            # Calculate completion percentages
            categories = state_copy["categories"]
            for cat_name, cat_data in categories.items():
                target = cat_data["target_count"]
                success = cat_data["success_count"]
                cat_data["completion_percentage"] = (success / target * 100) if target > 0 else 0
            
            # Create a simplified summary
            summary = {
                "crawler_info": {
                    "start_time": start_time_str,
                    "elapsed_time": elapsed_time,
                    "elapsed_time_str": self._format_duration(elapsed_time)
                },
                "overall_progress": {
                    "processed": state_copy["stats"]["urls_processed"],
                    "succeeded": state_copy["stats"]["urls_succeeded"],
                    "failed": state_copy["stats"]["urls_failed"],
                },
                "categories": {
                    cat_name: {
                        "target": cat_data["target_count"],
                        "success": cat_data["success_count"],
                        "completion": cat_data["completion_percentage"]
                    }
                    for cat_name, cat_data in categories.items()
                },
                "domains": {
                    domain: {
                        "success_count": data["success_count"],
                        "failure_count": data["failure_count"],
                        "average_time": data["average_time"]
                    }
                    for domain, data in state_copy["domains"].items()
                }
            }
            
            return summary
    
    def _format_duration(self, seconds: float) -> str:
        """Format seconds as a human-readable duration string."""
        hours, remainder = divmod(int(seconds), 3600)
        minutes, seconds = divmod(remainder, 60)
        return f"{hours}h {minutes}m {seconds}s"
    
    def cleanup(self):
        """Stop auto-save and perform final state save."""
        # Stop the auto-save thread
        self._stop_auto_save.set()
        if self._auto_save_thread:
            self._auto_save_thread.join(timeout=5)
            
        # Save one last time
        self.save()
        logger.info("CrawlerState cleanup complete")
