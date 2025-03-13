"""
AdaptiveRateLimiter - Dynamic rate limiting for web crawling

This module provides adaptive rate limiting capabilities to help crawl websites
responsibly while avoiding detection and server overload.
"""

import time
import random
import logging
from typing import Dict, Optional
from urllib.parse import urlparse

logger = logging.getLogger(__name__)

class AdaptiveRateLimiter:
    """
    Dynamically adjusts delay between requests based on server responses.
    
    Features:
    - Domain-specific delay tracking
    - Automatic backoff for failures
    - Gradual delay reduction after successful requests
    - Random jitter to mimic human behavior
    """
    
    def __init__(
        self, 
        default_delay: float = 2.0,
        min_delay: float = 0.5,
        max_delay: float = 60.0,
        backoff_factor: float = 2.0,
        success_factor: float = 0.9,
        jitter: float = 0.25
    ):
        """
        Initialize the rate limiter with configurable parameters.
        
        Args:
            default_delay: Default delay in seconds between requests
            min_delay: Minimum delay in seconds
            max_delay: Maximum delay in seconds
            backoff_factor: Multiplier for delay after failures
            success_factor: Multiplier for delay after successes (should be < 1)
            jitter: Maximum random jitter factor (0.25 = ±25%)
        """
        self.default_delay = default_delay
        self.min_delay = min_delay
        self.max_delay = max_delay
        self.backoff_factor = backoff_factor
        self.success_factor = success_factor
        self.jitter = jitter
        self.domain_delays: Dict[str, float] = {}
        logger.info(f"AdaptiveRateLimiter initialized with default delay of {default_delay}s")
    
    def _extract_domain(self, url: str) -> str:
        """Extract the domain from a URL."""
        try:
            return urlparse(url).netloc
        except Exception:
            return "default"
    
    def _add_jitter(self, delay: float) -> float:
        """Add random jitter to the delay."""
        jitter_amount = delay * self.jitter
        return delay + random.uniform(-jitter_amount, jitter_amount)
    
    def get_delay(self, url: Optional[str] = None) -> float:
        """
        Get the current delay for a specific domain.
        
        Args:
            url: URL to determine the domain-specific delay
            
        Returns:
            The current delay in seconds for the domain
        """
        if url is None:
            return self.default_delay
            
        domain = self._extract_domain(url)
        return self.domain_delays.get(domain, self.default_delay)
    
    def wait(self, url: Optional[str] = None) -> float:
        """
        Wait for the appropriate amount of time before making a request.
        
        Args:
            url: URL to determine the domain-specific delay
            
        Returns:
            The actual time waited in seconds
        """
        delay = self.get_delay(url)
        actual_delay = self._add_jitter(delay)
        
        if url:
            domain = self._extract_domain(url)
            logger.debug(f"Waiting {actual_delay:.2f}s for {domain}")
        else:
            logger.debug(f"Waiting {actual_delay:.2f}s")
            
        time.sleep(actual_delay)
        return actual_delay
    
    def success(self, url: str) -> None:
        """
        Register a successful request and reduce the delay slightly.
        
        Args:
            url: URL of the successful request
        """
        domain = self._extract_domain(url)
        current_delay = self.domain_delays.get(domain, self.default_delay)
        
        # Gradually decrease delay after successful requests, but not below min_delay
        new_delay = max(current_delay * self.success_factor, self.min_delay)
        self.domain_delays[domain] = new_delay
        
        logger.debug(f"Request to {domain} successful - delay reduced from {current_delay:.2f}s to {new_delay:.2f}s")
    
    def failure(self, url: str) -> float:
        """
        Register a failed request and increase the backoff delay.
        
        Args:
            url: URL of the failed request
            
        Returns:
            The new delay value
        """
        domain = self._extract_domain(url)
        current_delay = self.domain_delays.get(domain, self.default_delay)
        
        # Increase delay after failures, but not above max_delay
        new_delay = min(current_delay * self.backoff_factor, self.max_delay)
        self.domain_delays[domain] = new_delay
        
        logger.info(f"Request to {domain} failed - delay increased from {current_delay:.2f}s to {new_delay:.2f}s")
        return new_delay
    
    def reset_domain(self, url: str) -> None:
        """
        Reset the delay for a specific domain to the default value.
        
        Args:
            url: URL to determine the domain to reset
        """
        domain = self._extract_domain(url)
        self.domain_delays[domain] = self.default_delay
        logger.debug(f"Rate limiter reset for {domain}")
    
    def get_domain_stats(self) -> Dict[str, float]:
        """
        Get the current delay for all tracked domains.
        
        Returns:
            Dictionary mapping domain names to their current delays
        """
        return dict(self.domain_delays)
