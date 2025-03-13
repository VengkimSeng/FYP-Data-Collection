"""
BrowserManager - Manages a pool of browser instances for web scraping

This module provides functionality to create, manage, and rotate browser instances,
optimizing resource usage and improving crawling reliability.
"""

import os
import time
import logging
import platform
import random
import psutil
import threading
from typing import Dict, List, Optional, Tuple
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from selenium.common.exceptions import WebDriverException

# Import the chrome_setup module
import sys
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from src.utils.chrome_setup import setup_chrome_driver

logger = logging.getLogger(__name__)

class BrowserManager:
    """
    Manages a pool of browser instances for efficient web scraping.
    
    Features:
    - Maintains a pool of reusable browser instances
    - Auto-detects ChromeDriver path
    - Implements browser rotation with page count tracking
    - Handles browser cleanup and crash recovery
    - Optimizes Chrome settings for performance and anti-detection
    """
    
    def __init__(
        self, 
        pool_size: int = 3, 
        pages_per_browser: int = 50,
        max_browser_lifetime: int = 3600,  # In seconds (1 hour)
        headless: bool = True,
        disable_images: bool = True,
        random_user_agent: bool = True,
        auto_detect_driver: bool = True,
        chromedriver_path: Optional[str] = None
    ):
        """
        Initialize the browser manager with configurable parameters.
        
        Args:
            pool_size: Maximum number of browser instances
            pages_per_browser: Maximum pages to load before browser rotation
            max_browser_lifetime: Maximum browser lifetime in seconds
            headless: Whether to run browsers in headless mode
            disable_images: Whether to disable images
            random_user_agent: Whether to use random user agents
            auto_detect_driver: Whether to auto-detect ChromeDriver
            chromedriver_path: Path to ChromeDriver executable (optional)
        """
        self.pool_size = pool_size
        self.pages_per_browser = pages_per_browser
        self.max_browser_lifetime = max_browser_lifetime
        self.headless = headless
        self.disable_images = disable_images
        self.random_user_agent = random_user_agent
        self.auto_detect_driver = auto_detect_driver
        self.chromedriver_path = chromedriver_path
        
        # Pool of browser instances
        self.browsers: List[Dict[str, any]] = []
        self.pool_lock = threading.RLock()  # Reentrant lock for thread safety
        
        # Track active browsers
        self.active_browsers = 0
        
        # Auto-detect ChromeDriver if path not provided
        if auto_detect_driver and not chromedriver_path:
            self.chromedriver_path = self._detect_chrome_driver()
            
        logger.info(f"BrowserManager initialized with pool size {pool_size}")
        logger.info(f"Using ChromeDriver path: {self.chromedriver_path}")
    
    def _detect_chrome_driver(self) -> Optional[str]:
        """
        Auto-detect ChromeDriver path based on OS.
        
        Returns:
            Path to ChromeDriver executable or None if not found
        """
        system = platform.system().lower()
        possible_paths = []
        
        if system == "darwin":  # macOS
            possible_paths = [
                "/usr/local/bin/chromedriver",
                "/opt/homebrew/bin/chromedriver",
                os.path.expanduser("~/chromedriver")
            ]
        elif system == "linux":
            possible_paths = [
                "/usr/bin/chromedriver",
                "/usr/local/bin/chromedriver",
                os.path.expanduser("~/chromedriver")
            ]
        elif system == "windows":
            possible_paths = [
                "C:\\chromedriver.exe",
                os.path.join(os.environ.get("LOCALAPPDATA", ""), "chromedriver.exe"),
                os.path.join(os.environ.get("ProgramFiles", ""), "chromedriver.exe"),
                os.path.join(os.environ.get("ProgramFiles(x86)", ""), "chromedriver.exe")
            ]
            
        # Check each path
        for path in possible_paths:
            if os.path.exists(path) and os.access(path, os.X_OK):
                logger.info(f"Found ChromeDriver at: {path}")
                return path
                
        logger.warning("ChromeDriver not found in common locations. Will use WebDriver Manager.")
        return None
    
    def _create_browser(self) -> Dict[str, any]:
        """
        Create a new browser instance with optimal settings.
        
        Returns:
            Dictionary with browser instance and metadata
        """
        try:
            # Create a browser using the chrome_setup module
            driver = setup_chrome_driver(
                chromedriver_path=self.chromedriver_path,
                headless=self.headless,
                disable_images=self.disable_images,
                random_user_agent=self.random_user_agent,
                use_webdriver_manager=True
            )
            
            # Set script timeout longer than the default
            driver.set_script_timeout(30)
            driver.set_page_load_timeout(60)
            
            # Configure the browser to avoid detection
            driver.execute_cdp_cmd("Page.addScriptToEvaluateOnNewDocument", {
                "source": """
                    Object.defineProperty(navigator, 'webdriver', {
                        get: () => undefined
                    });
                """
            })
            
            browser_info = {
                "driver": driver,
                "created_at": time.time(),
                "page_count": 0,
                "id": random.randint(10000, 99999),  # Unique ID for tracking
                "in_use": False,
                "last_used": time.time()
            }
            
            logger.info(f"Created browser #{browser_info['id']}")
            return browser_info
            
        except Exception as e:
            logger.error(f"Failed to create browser: {e}")
            raise
    
    def get_browser(self, url: Optional[str] = None) -> Tuple[webdriver.Chrome, int]:
        """
        Get a browser instance from the pool or create a new one.
        
        Args:
            url: Optional URL context for browser selection
            
        Returns:
            Tuple of (browser instance, browser ID)
        """
        with self.pool_lock:
            # Look for an available browser
            available_browser = None
            
            # Check memory usage before getting a browser
            memory_percent = psutil.virtual_memory().percent
            if memory_percent > 90:
                logger.warning(f"High memory usage detected ({memory_percent}%). Cleaning browser pool.")
                self._clean_pool(force=True)
            
            # Try to find an available browser
            for browser in self.browsers:
                if not browser["in_use"]:
                    available_browser = browser
                    break
                    
            # If no available browsers, check if we can create a new one
            if available_browser is None and len(self.browsers) < self.pool_size:
                try:
                    available_browser = self._create_browser()
                    self.browsers.append(available_browser)
                except Exception as e:
                    logger.error(f"Failed to create a new browser: {e}")
                    # Try to reuse an existing browser as a fallback
                    if self.browsers:
                        # Pick the one with the lowest page count
                        available_browser = min(self.browsers, key=lambda b: b["page_count"])
                        logger.warning(f"Reusing browser #{available_browser['id']} as fallback")
            
            # If we still don't have a browser, wait for one to become available
            if available_browser is None:
                logger.warning("No browsers available, waiting for one to become available")
                # Sort by page count and select the one with the lowest
                self.browsers.sort(key=lambda b: b["page_count"])
                available_browser = self.browsers[0]
            
            # Mark the browser as in use
            available_browser["in_use"] = True
            available_browser["last_used"] = time.time()
            browser_id = available_browser["id"]
            
            logger.debug(f"Using browser #{browser_id} (pages: {available_browser['page_count']})")
            self.active_browsers += 1
            
            return available_browser["driver"], browser_id
    
    def release_browser(self, browser_id: int, increment_count: bool = True, success: bool = True):
        """
        Release a browser back to the pool.
        
        Args:
            browser_id: ID of the browser to release
            increment_count: Whether to increment the page count
            success: Whether the browser was used successfully
        """
        with self.pool_lock:
            for browser in self.browsers:
                if browser["id"] == browser_id:
                    browser["in_use"] = False
                    browser["last_used"] = time.time()
                    
                    if increment_count:
                        browser["page_count"] += 1
                    
                    # If browser had an error or reached page limit, mark for rotation
                    if (not success or 
                        browser["page_count"] >= self.pages_per_browser or
                        time.time() - browser["created_at"] > self.max_browser_lifetime):
                        
                        logger.info(f"Browser #{browser_id} marked for rotation")
                        self._rotate_browser(browser_id)
                    
                    self.active_browsers = max(0, self.active_browsers - 1)
                    break
    
    def _rotate_browser(self, browser_id: int):
        """
        Replace an old browser instance with a fresh one.
        
        Args:
            browser_id: ID of the browser to rotate
        """
        with self.pool_lock:
            for i, browser in enumerate(self.browsers):
                if browser["id"] == browser_id and not browser["in_use"]:
                    logger.info(f"Rotating browser #{browser_id} after {browser['page_count']} pages")
                    
                    # Close the old browser
                    try:
                        browser["driver"].quit()
                    except Exception as e:
                        logger.warning(f"Error closing browser #{browser_id}: {e}")
                    
                    # Create a new browser to replace it
                    try:
                        new_browser = self._create_browser()
                        self.browsers[i] = new_browser
                        logger.info(f"Browser #{browser_id} replaced with #{new_browser['id']}")
                    except Exception as e:
                        logger.error(f"Failed to create replacement browser: {e}")
                        # Remove the dead browser from the pool
                        self.browsers.pop(i)
                        logger.warning(f"Removed browser #{browser_id} from pool without replacement")
                    break
    
    def _clean_pool(self, force: bool = False):
        """
        Clean up the browser pool by removing unused browsers.
        
        Args:
            force: Whether to force cleanup of all inactive browsers
        """
        with self.pool_lock:
            current_time = time.time()
            
            to_remove = []
            for i, browser in enumerate(self.browsers):
                # Skip browsers that are in use
                if browser["in_use"]:
                    continue
                
                # Remove if forced or not used recently
                if force or current_time - browser["last_used"] > 300:  # 5 minutes
                    logger.info(f"Cleaning up browser #{browser['id']}")
                    to_remove.append(i)
                    try:
                        browser["driver"].quit()
                    except Exception as e:
                        logger.warning(f"Error closing browser #{browser['id']}: {e}")
            
            # Remove browsers from the pool (in reverse order to avoid index issues)
            for i in sorted(to_remove, reverse=True):
                self.browsers.pop(i)
    
    def clean_up(self):
        """Close all browser instances and clean up resources."""
        logger.info("Cleaning up all browser instances")
        with self.pool_lock:
            for browser in self.browsers:
                try:
                    browser["driver"].quit()
                except Exception as e:
                    logger.warning(f"Error closing browser #{browser['id']}: {e}")
            
            self.browsers = []
            self.active_browsers = 0
    
    def handle_browser_error(self, browser_id: int, error: Exception) -> bool:
        """
        Handle browser errors by recovering or rotating the browser.
        
        Args:
            browser_id: ID of the browser with an error
            error: Exception that occurred
            
        Returns:
            True if the browser needs to be rotated, False otherwise
        """
        logger.warning(f"Browser #{browser_id} encountered an error: {error}")
        
        # Determine if this is a fatal error
        is_fatal = isinstance(error, (WebDriverException)) and any(
            msg in str(error).lower() 
            for msg in ["crashed", "disconnect", "closed", "killed", "terminated"]
        )
        
        with self.pool_lock:
            for browser in self.browsers:
                if browser["id"] == browser_id:
                    if is_fatal:
                        logger.error(f"Fatal error for browser #{browser_id}, marking for rotation")
                        if not browser["in_use"]:
                            self._rotate_browser(browser_id)
                        return True
                    else:
                        # Non-fatal errors - reset state if possible
                        try:
                            browser["driver"].execute_script("window.stop();")
                        except:
                            pass
                        return False
        
        return False
