"""
SmartRetry - Intelligent retry decorator with backoff and exception handling

This module provides a decorator for automatically retrying operations with
configurable backoff, randomized delays, and exception-specific handling.
"""

import time
import random
import logging
import functools
from typing import Callable, Type, List, Union, Dict, Optional, Any
import traceback

logger = logging.getLogger(__name__)

class SmartRetry:
    """
    Decorator for retrying functions with exponential backoff and jitter.
    
    Features:
    - Exponential backoff with configurable settings
    - Random jitter to prevent retry storms
    - Conditional retrying based on result or exception
    - Detailed retry logging
    """
    
    def __init__(
        self,
        max_tries: int = 3,
        initial_delay: float = 1.0,
        max_delay: float = 60.0,
        backoff_factor: float = 2.0,
        jitter: float = 0.1,
        exceptions_to_retry: List[Type[Exception]] = None,
        exceptions_to_ignore: List[Type[Exception]] = None,
        should_retry_fn: Callable[[Any], bool] = None
    ):
        """
        Initialize the retry decorator with configurable parameters.
        
        Args:
            max_tries: Maximum number of attempts
            initial_delay: Initial delay between retries in seconds
            max_delay: Maximum delay between retries in seconds
            backoff_factor: Multiplier for delay after each retry
            jitter: Random jitter factor to add to delay (0.1 = ±10%)
            exceptions_to_retry: List of exception types to retry
            exceptions_to_ignore: List of exception types to ignore (no retry)
            should_retry_fn: Function to determine if result warrants a retry
        """
        self.max_tries = max_tries
        self.initial_delay = initial_delay
        self.max_delay = max_delay
        self.backoff_factor = backoff_factor
        self.jitter = jitter
        
        # Default to retrying all exceptions
        self.exceptions_to_retry = exceptions_to_retry or [Exception]
        self.exceptions_to_ignore = exceptions_to_ignore or []
        
        # Function to determine if result warrants a retry
        self.should_retry_fn = should_retry_fn
    
    def __call__(self, func):
        """
        Apply the retry decorator to a function.
        
        Args:
            func: Function to decorate
            
        Returns:
            Decorated function with retry logic
        """
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            """Wrapper function that implements retry logic."""
            tries = 0
            delay = self.initial_delay
            last_exception = None
            
            # Try calling the function up to max_tries times
            while tries < self.max_tries:
                try:
                    # Attempt to call the function
                    result = func(*args, **kwargs)
                    
                    # If a should_retry_fn is provided, check if we should retry
                    if self.should_retry_fn and tries < self.max_tries - 1:
                        if self.should_retry_fn(result):
                            tries += 1
                            delay = self._calculate_delay(delay, tries)
                            logger.info(
                                f"Retry condition met for {func.__name__}, "
                                f"retrying in {delay:.2f}s (attempt {tries+1}/{self.max_tries})"
                            )
                            time.sleep(delay)
                            continue
                    
                    # Function succeeded, return the result
                    return result
                    
                except tuple(self.exceptions_to_retry) as e:
                    # Check if this exception should be ignored
                    if any(isinstance(e, exc) for exc in self.exceptions_to_ignore):
                        logger.warning(f"Ignored exception in {func.__name__}: {e}")
                        raise
                    
                    # Log the exception
                    last_exception = e
                    tries += 1
                    
                    # If we've run out of retries, re-raise the exception
                    if tries >= self.max_tries:
                        logger.error(
                            f"Max retries ({self.max_tries}) exceeded for {func.__name__}: {e}"
                        )
                        raise
                    
                    # Calculate delay for next retry
                    delay = self._calculate_delay(delay, tries)
                    
                    # Log the retry
                    logger.warning(
                        f"Exception in {func.__name__} (attempt {tries}/{self.max_tries}): {e}. "
                        f"Retrying in {delay:.2f}s"
                    )
                    
                    # Include stack trace for debugging at DEBUG level
                    logger.debug(f"Stack trace for retry: {traceback.format_exc()}")
                    
                    # Wait before retrying
                    time.sleep(delay)
            
            # Should never reach here, but just in case
            if last_exception:
                raise last_exception
            
            # Also should never reach here
            return None
        
        return wrapper
    
    def _calculate_delay(self, current_delay: float, attempt: int) -> float:
        """
        Calculate the next retry delay with exponential backoff and jitter.
        
        Args:
            current_delay: Current delay in seconds
            attempt: Current attempt number
            
        Returns:
            Next delay in seconds
        """
        # Calculate delay with exponential backoff
        delay = min(current_delay * self.backoff_factor, self.max_delay)
        
        # Add jitter
        jitter_amount = delay * self.jitter
        delay = random.uniform(delay - jitter_amount, delay + jitter_amount)
        
        return max(0, delay)  # Ensure delay is non-negative

# Predefined retry configurations for common scenarios
def default_retry(max_tries: int = 3):
    """Default retry configuration with reasonable defaults."""
    return SmartRetry(
        max_tries=max_tries,
        initial_delay=1.0,
        backoff_factor=2.0,
        jitter=0.1
    )

def network_retry(max_tries: int = 5):
    """Retry configuration optimized for network operations."""
    import requests
    from urllib3.exceptions import HTTPError
    
    return SmartRetry(
        max_tries=max_tries,
        initial_delay=2.0,
        backoff_factor=2.0,
        jitter=0.25,
        exceptions_to_retry=[
            requests.exceptions.RequestException,
            ConnectionError,
            TimeoutError,
            HTTPError
        ]
    )

def selenium_retry(max_tries: int = 3):
    """Retry configuration optimized for Selenium operations."""
    from selenium.common.exceptions import (
        WebDriverException, 
        StaleElementReferenceException,
        TimeoutException
    )
    
    return SmartRetry(
        max_tries=max_tries,
        initial_delay=1.0,
        backoff_factor=2.0,
        jitter=0.2,
        exceptions_to_retry=[
            WebDriverException,
            StaleElementReferenceException,
            TimeoutException
        ],
        exceptions_to_ignore=[
            KeyboardInterrupt,
            SystemExit
        ]
    )
