"""
Crawler Utilities - Common utility functions for web crawlers

This module provides utility functions used by the master crawler controller
and individual crawler modules.
"""

import os
import sys
import logging
import importlib
import argparse
import time
import gc
import psutil
from typing import Dict, List, Set, Any

logger = logging.getLogger(__name__)

# Required packages with version constraints
REQUIRED_PACKAGES = {
    "selenium": ">=4.0.0",
    "bs4": ">=4.9.0",
    "requests": ">=2.25.0",
    "psutil": ">=5.8.0",
    "webdriver_manager": ">=3.5.0"
}

def check_required_packages():
    """Check if required packages are installed with correct versions."""
    missing = []
    for package, version in REQUIRED_PACKAGES.items():
        try:
            importlib.import_module(package)
        except ImportError:
            missing.append(f"{package}{version}")
    
    if missing:
        print("\n⚠️  Missing required Python packages ⚠️")
        print(f"pip install {' '.join(missing)}")
        sys.exit(1)

def parse_arguments():
    """Parse command-line arguments."""
    parser = argparse.ArgumentParser(description="Smart web crawler controller")
    
    # Basic arguments
    parser.add_argument("--urls-per-category", type=int, default=2500)
    parser.add_argument("--max-workers", type=int, default=3)
    parser.add_argument("--categories-file", type=str, default="config/categories.json")
    parser.add_argument("--output-dir", type=str, default="output/urls")
    parser.add_argument("--resume", action="store_true")
    parser.add_argument("--reset", action="store_true")
    parser.add_argument("--min-urls-per-source", type=int, default=50)
    
    # Smart crawling parameters
    parser.add_argument("--browser-pool-size", type=int, default=3)
    parser.add_argument("--quality-threshold", type=int, default=50)
    parser.add_argument("--rate-limit-delay", type=float, default=2.0)
    parser.add_argument("--state-file", type=str, default="crawler_state.json")
    parser.add_argument("--similarity-threshold", type=float, default=0.85)
    parser.add_argument("--max-domain-percentage", type=float, default=25.0)
    
    return parser.parse_args()

def check_memory_usage(components=None):
    """Check system memory usage and take action if needed."""
    current_time = time.time()
    
    # Get memory usage
    memory = psutil.virtual_memory()
    memory_percent = memory.percent
    
    # Log memory usage
    logger.info(f"Memory: {memory_percent:.1f}% (Used: {memory.used/1024**3:.1f}GB)")
    
    # Perform garbage collection if memory is high
    if memory_percent > 80:
        gc.collect()
        if components and components.browser_manager:
            components.browser_manager._clean_pool(force=True)

class CrawlerComponents:
    """Container class for all components needed by the crawler system."""
    
    def __init__(self, state_file="crawler_state.json"):
        """Initialize components required for the crawler."""
        from src.utils.browser_manager import BrowserManager
        from src.utils.crawler_state import CrawlerState
        
        self.browser_manager = BrowserManager()
        self.crawler_state = CrawlerState(state_file=state_file)
        self.stats = {
            "urls_processed": 0,
            "urls_collected": 0,
            "errors": 0
        }
        
    def cleanup(self):
        """Clean up all components."""
        if hasattr(self, 'browser_manager'):
            self.browser_manager.clean_up()
        if hasattr(self, 'crawler_state'):
            self.crawler_state.cleanup()
            
    def __del__(self):
        """Ensure cleanup when object is deleted."""
        self.cleanup()

def setup_smart_components(args):
    """Initialize and configure smart crawler components."""
    # Import required components
    from src.utils.adaptive_rate_limiter import AdaptiveRateLimiter
    from src.utils.browser_manager import BrowserManager 
    from src.utils.smart_url_queue import SmartURLQueue
    from src.utils.content_quality_analyzer import ContentQualityAnalyzer
    from src.utils.content_fingerprinter import ContentFingerprinter
    from src.utils.crawler_state import CrawlerState
    
    # Create components with configuration from args
    # Use getattr to safely access attributes that might be missing
    state_file = getattr(args, 'state_file', 'crawler_state.json')
    components = CrawlerComponents(state_file=state_file)
    
    # Initialize components with safe parameter access
    rate_limit_delay = getattr(args, 'rate_limit_delay', 2.0)
    browser_pool_size = getattr(args, 'browser_pool_size', 3)
    max_domain_percentage = getattr(args, 'max_domain_percentage', 25.0)
    similarity_threshold = getattr(args, 'similarity_threshold', 0.85)
    
    components.rate_limiter = AdaptiveRateLimiter(default_delay=rate_limit_delay)
    components.browser_manager = BrowserManager(pool_size=browser_pool_size)
    components.url_queue = SmartURLQueue(max_per_domain_percentage=max_domain_percentage)
    components.quality_analyzer = ContentQualityAnalyzer()
    components.fingerprinter = ContentFingerprinter(similarity_threshold=similarity_threshold)
    # We already created crawler_state in the CrawlerComponents constructor
    
    return components
