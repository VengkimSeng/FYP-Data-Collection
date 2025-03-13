"""
SmartURLQueue - Intelligent URL queue with domain-based rate limiting and prioritization

This module provides a smart URL queue for managing crawl targets with built-in
domain-based rate limiting, category quotas, and duplicate detection.
"""

import time
import logging
import threading
import heapq
from typing import Dict, List, Set, Tuple, Optional, NamedTuple
from urllib.parse import urlparse
from collections import defaultdict, Counter

logger = logging.getLogger(__name__)

class URLItem(NamedTuple):
    """Represents a URL in the priority queue."""
    priority: float  # Lower is higher priority
    timestamp: float
    url: str
    category: str
    domain: str
    source_url: str

class SmartURLQueue:
    """
    Maintains a priority queue of URLs with domain-based rate limiting.
    
    Features:
    - Priority queue with domain-based rate limiting
    - Category quota tracking
    - Duplicate URL prevention
    - Collection progress statistics
    """
    
    def __init__(
        self,
        domain_delay: float = 2.0,
        category_quotas: Dict[str, int] = None,
        max_per_domain_percentage: float = 25.0,
        allow_duplicates: bool = False
    ):
        """
        Initialize the URL queue with configurable parameters.
        
        Args:
            domain_delay: Minimum delay between requests to the same domain
            category_quotas: Maximum URLs to collect per category
            max_per_domain_percentage: Maximum percentage of URLs from a single domain
            allow_duplicates: Whether to allow duplicate URLs
        """
        self.domain_delay = domain_delay
        self.category_quotas = category_quotas or {}
        self.max_per_domain_percentage = max_per_domain_percentage
        self.allow_duplicates = allow_duplicates
        
        # Priority queue for URLs
        self.queue: List[URLItem] = []
        
        # Track the next available time for each domain
        self.domain_next_available: Dict[str, float] = {}
        
        # Track URLs that have been seen
        self.seen_urls: Set[str] = set()
        
        # Track URLs per domain and category
        self.urls_per_domain: Counter = Counter()
        self.urls_per_category: Counter = Counter()
        self.processed_per_category: Counter = Counter()
        
        # Lock for thread safety
        self.lock = threading.RLock()
        
        logger.info(f"SmartURLQueue initialized with domain delay {domain_delay}s")
        if category_quotas:
            logger.info(f"Category quotas: {category_quotas}")
    
    def _extract_domain(self, url: str) -> str:
        """Extract the domain from a URL."""
        try:
            return urlparse(url).netloc
        except Exception:
            return "unknown"
    
    def add_url(
        self, 
        url: str, 
        category: str,
        priority: float = 1.0,
        source_url: Optional[str] = None
    ) -> bool:
        """
        Add a URL to the queue with a given priority.
        
        Args:
            url: URL to add
            category: Category of the URL (for quota tracking)
            priority: Priority value (lower is higher priority)
            source_url: Source URL from which this URL was discovered
            
        Returns:
            Whether the URL was added (False if duplicate or quota reached)
        """
        with self.lock:
            # Skip if URL has been seen and duplicates are not allowed
            if url in self.seen_urls and not self.allow_duplicates:
                logger.debug(f"Skipping duplicate URL: {url}")
                return False
            
            # Check if category quota has been reached
            if category in self.category_quotas:
                quota = self.category_quotas[category]
                if self.urls_per_category[category] >= quota:
                    logger.debug(f"Quota reached for category '{category}' ({quota} URLs)")
                    return False
            
            domain = self._extract_domain(url)
            
            # Check if this domain has too many URLs already
            total_urls = sum(self.urls_per_category.values())
            if total_urls > 0 and domain in self.urls_per_domain:
                domain_percentage = (self.urls_per_domain[domain] / total_urls) * 100
                if domain_percentage > self.max_per_domain_percentage:
                    logger.debug(
                        f"Domain {domain} has {domain_percentage:.1f}% of URLs "
                        f"(> {self.max_per_domain_percentage}% limit)"
                    )
                    return False
            
            # Calculate the earliest time this domain can be crawled
            current_time = time.time()
            next_available = max(
                current_time,
                self.domain_next_available.get(domain, 0)
            )
            
            # Add to the priority queue
            timestamp = time.time()  # Used as a tie-breaker
            heapq.heappush(
                self.queue, 
                URLItem(
                    priority=priority,
                    timestamp=timestamp,
                    url=url,
                    category=category,
                    domain=domain,
                    source_url=source_url or url
                )
            )
            
            # Mark as seen
            self.seen_urls.add(url)
            
            # Update tracking counters
            self.urls_per_domain[domain] += 1
            self.urls_per_category[category] += 1
            
            logger.debug(f"Added URL: {url} (category: {category}, priority: {priority})")
            return True
    
    def add_urls(self, urls: List[str], category: str, priority: float = 1.0, source_url: Optional[str] = None) -> int:
        """
        Add multiple URLs to the queue.
        
        Args:
            urls: List of URLs to add
            category: Category for all URLs
            priority: Priority for all URLs
            source_url: Source URL from which these URLs were discovered
            
        Returns:
            Number of URLs successfully added
        """
        added_count = 0
        for url in urls:
            if self.add_url(url, category, priority, source_url):
                added_count += 1
        return added_count
    
    def get_next_url(self) -> Optional[Tuple[str, str, str]]:
        """
        Get the next URL to crawl based on priority and domain rate limiting.
        
        Returns:
            Tuple of (URL, category, source_url) or None if queue is empty
        """
        with self.lock:
            current_time = time.time()
            
            # Try to find a URL from a domain that's available now
            skipped_items = []
            result = None
            
            while self.queue and result is None:
                # Get the highest priority item
                item = heapq.heappop(self.queue)
                
                # Check if this domain is available
                next_available = self.domain_next_available.get(item.domain, 0)
                
                if next_available <= current_time:
                    # Domain is available, use this URL
                    self.domain_next_available[item.domain] = current_time + self.domain_delay
                    self.processed_per_category[item.category] += 1
                    result = (item.url, item.category, item.source_url)
                else:
                    # Domain not available yet, skip for now
                    skipped_items.append(item)
            
            # Put back any skipped items
            for item in skipped_items:
                heapq.heappush(self.queue, item)
            
            if result:
                logger.debug(f"Retrieved URL: {result[0]} (category: {result[1]})")
                
            return result
    
    def get_stats(self) -> Dict[str, any]:
        """
        Get statistics about the queue.
        
        Returns:
            Dictionary with queue statistics
        """
        with self.lock:
            stats = {
                "queue_size": len(self.queue),
                "domains": {
                    "count": len(self.urls_per_domain),
                    "distribution": dict(self.urls_per_domain)
                },
                "categories": {
                    "queued": dict(self.urls_per_category),
                    "processed": dict(self.processed_per_category)
                },
                "total_urls_seen": len(self.seen_urls)
            }
            
            # Calculate percentage complete for each category
            stats["categories"]["completion"] = {}
            for category, quota in self.category_quotas.items():
                processed = self.processed_per_category.get(category, 0)
                completion = (processed / quota * 100) if quota else 0
                stats["categories"]["completion"][category] = completion
                
            return stats
    
    def reset_category_quota(self, category: str, new_quota: int):
        """
        Reset the quota for a specific category.
        
        Args:
            category: Category to reset
            new_quota: New quota value
        """
        with self.lock:
            self.category_quotas[category] = new_quota
            logger.info(f"Reset quota for category '{category}' to {new_quota}")
    
    def set_domain_delay(self, domain: str, delay: float):
        """
        Set a custom delay for a specific domain.
        
        Args:
            domain: Domain to set delay for
            delay: New delay value in seconds
        """
        with self.lock:
            # Reset the next available time
            current_time = time.time()
            self.domain_next_available[domain] = current_time + delay
            logger.info(f"Set custom delay for domain {domain} to {delay}s")
    
    def is_empty(self) -> bool:
        """
        Check if the queue is empty.
        
        Returns:
            True if the queue is empty, False otherwise
        """
        with self.lock:
            return len(self.queue) == 0
    
    def size(self) -> int:
        """
        Get the current size of the queue.
        
        Returns:
            Number of URLs in the queue
        """
        with self.lock:
            return len(self.queue)
    
    def clear_category(self, category: str):
        """
        Remove all URLs from a specific category.
        
        Args:
            category: Category to clear
        """
        with self.lock:
            # Create a new queue without the specified category
            new_queue = []
            while self.queue:
                item = heapq.heappop(self.queue)
                if item.category != category:
                    new_queue.append(item)
                    
            # Replace the queue
            self.queue = new_queue
            heapq.heapify(self.queue)
            
            # Update tracking counters
            self.urls_per_category[category] = 0
            
            logger.info(f"Cleared all URLs for category '{category}'")
    
    def clear_all(self):
        """Clear all URLs from the queue."""
        with self.lock:
            self.queue = []
            self.seen_urls.clear()
            self.urls_per_domain.clear()
            self.urls_per_category.clear()
            self.processed_per_category.clear()
            self.domain_next_available.clear()
            logger.info("Cleared all URLs from queue")
