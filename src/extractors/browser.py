"""
Browser setup and management for article extractor.
"""

import os
import platform
import time
from typing import Optional
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from webdriver_manager.chrome import ChromeDriverManager
import logging
from src.extractors.logger import log_debug, log_error

def get_chrome_options(headless: bool = True, no_images: bool = True) -> Options:
    """
    Get Chrome options for Selenium WebDriver.
    
    Args:
        headless: Whether to run in headless mode
        no_images: Whether to disable image loading
        
    Returns:
        Configured Chrome options
    """
    options = Options()
    
    if headless:
        options.add_argument('--headless')
        
    options.add_argument('--no-sandbox')
    options.add_argument('--disable-dev-shm-usage')
    
    if no_images:
        options.add_experimental_option(
            'prefs', {'profile.managed_default_content_settings.images': 2}
        )
    
    return options

def create_driver(headless: bool = True, no_images: bool = True, timeout: int = 30) -> webdriver.Chrome:
    """
    Create a Selenium Chrome WebDriver.
    
    Args:
        headless: Whether to run in headless mode
        no_images: Whether to disable image loading
        timeout: Page load timeout in seconds
        
    Returns:
        Configured Chrome WebDriver
    """
    try:
        options = get_chrome_options(headless, no_images)
        
        service = Service(ChromeDriverManager().install())
        driver = webdriver.Chrome(service=service, options=options)
        log_debug("Created Chrome driver using webdriver-manager")
        
        # Configure timeout
        driver.set_page_load_timeout(timeout)
        driver.implicitly_wait(10)  # Wait up to 10 seconds for elements to appear
        
        return driver
        
    except Exception as e:
        log_error(f"Error creating Chrome driver: {e}")
        raise

def close_driver(driver: Optional[webdriver.Chrome]) -> None:
    """
    Safely close a WebDriver.
    
    Args:
        driver: WebDriver to close
    """
    if driver:
        try:
            driver.quit()
            log_debug("Chrome driver closed successfully")
        except Exception as e:
            log_error(f"Error closing Chrome driver: {e}")
