"""
Chrome WebDriver Setup Module

This module provides functions to set up and configure Chrome WebDriver for web scraping
across different operating systems and environments.
"""

import os
import random
import platform
import logging
import shutil
from typing import Optional, List, Dict, Any

from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.common.exceptions import WebDriverException

# Configure logger
logger = logging.getLogger(__name__)

def get_default_chromedriver_path() -> Optional[str]:
    """
    Determine the default ChromeDriver path based on the operating system.
    
    Returns:
        Optional path to ChromeDriver executable
    """
    system = platform.system()
    
    # Try to find ChromeDriver in PATH
    chromedriver_name = "chromedriver.exe" if system == "Windows" else "chromedriver"
    path_chromedriver = shutil.which(chromedriver_name)
    if path_chromedriver:
        return path_chromedriver
        
    # System-specific default paths
    if system == "Windows":
        return "C:\\Program Files\\chromedriver-win64\\chromedriver.exe"
    elif system == "Darwin":  # macOS
        return "/opt/homebrew/bin/chromedriver"
    elif system == "Linux":
        return "/usr/bin/chromedriver"
    
    return None

def get_random_user_agent() -> str:
    """
    Get a random user agent string to avoid detection.
    
    Returns:
        Random user agent string
    """
    user_agents = [
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36",
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36",
        "Mozilla/5.0 (X11; Ubuntu; Linux x86_64; rv:89.0) Gecko/20100101 Firefox/89.0",
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/92.0.4515.107 Safari/537.36",
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 11_5_1) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/92.0.4515.107 Safari/537.36",
    ]
    return random.choice(user_agents)

def setup_chrome_options(
    headless: bool = True,
    disable_images: bool = True,
    random_user_agent: bool = True,
    additional_arguments: Optional[List[str]] = None,
    additional_preferences: Optional[Dict[str, Any]] = None
) -> Options:
    """
    Configure Chrome options for web scraping.
    
    Args:
        headless: Run browser in headless mode
        disable_images: Disable image loading for faster browsing
        random_user_agent: Use a random user agent
        additional_arguments: Additional Chrome arguments
        additional_preferences: Additional Chrome preferences
        
    Returns:
        Configured Chrome options
    """
    options = Options()
    
    # Basic arguments for web scraping
    if headless:
        options.add_argument("--headless")
    
    options.add_argument("--disable-gpu")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--disable-blink-features=AutomationControlled")
    
    # Add random user agent if requested
    if random_user_agent:
        options.add_argument(f"user-agent={get_random_user_agent()}")
    
    # Disable images if requested
    if disable_images:
        prefs = {"profile.managed_default_content_settings.images": 2}
        options.add_experimental_option("prefs", prefs)
    
    # Add any additional arguments
    if additional_arguments:
        for arg in additional_arguments:
            options.add_argument(arg)
    
    # Add any additional preferences
    if additional_preferences:
        prefs = options.experimental_options.get("prefs", {})
        prefs.update(additional_preferences)
        options.add_experimental_option("prefs", prefs)
    
    return options

def setup_chrome_driver(
    chromedriver_path: Optional[str] = None,
    options: Optional[Options] = None,
    headless: bool = True,
    disable_images: bool = True,
    random_user_agent: bool = True,
    use_webdriver_manager: bool = True
) -> webdriver.Chrome:
    """
    Set up and configure Chrome WebDriver with optimized settings.
    
    Args:
        chromedriver_path: Path to ChromeDriver executable
        options: Preconfigured Chrome options (if None, will create default options)
        headless: Run browser in headless mode (if creating new options)
        disable_images: Disable image loading (if creating new options)
        random_user_agent: Use random user agent (if creating new options)
        use_webdriver_manager: Try using webdriver_manager as fallback if path not found
        
    Returns:
        Configured Chrome WebDriver instance
    """
    # Use provided options or create new ones
    chrome_options = options if options else setup_chrome_options(
        headless=headless,
        disable_images=disable_images,
        random_user_agent=random_user_agent
    )
    
    # Set macOS Chrome binary location if appropriate
    if platform.system() == "Darwin":
        if os.path.exists("/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"):
            chrome_options.binary_location = "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"
    
    # Try different methods to initialize the driver
    driver = None
    errors = []
    
    # Method 1: Use the specified ChromeDriver path
    if chromedriver_path and os.path.exists(chromedriver_path):
        try:
            logger.info(f"Trying ChromeDriver from specified path: {chromedriver_path}")
            driver = webdriver.Chrome(service=Service(chromedriver_path), options=chrome_options)
            return driver
        except Exception as e:
            errors.append(f"Failed with specified path: {str(e)}")
    
    # Method 2: Use default ChromeDriver path
    if not chromedriver_path:
        chromedriver_path = get_default_chromedriver_path()
        if chromedriver_path and os.path.exists(chromedriver_path):
            try:
                logger.info(f"Trying ChromeDriver from default path: {chromedriver_path}")
                driver = webdriver.Chrome(service=Service(chromedriver_path), options=chrome_options)
                return driver
            except Exception as e:
                errors.append(f"Failed with default path: {str(e)}")
    
    # Method 3: Use webdriver_manager if enabled
    if use_webdriver_manager:
        try:
            from webdriver_manager.chrome import ChromeDriverManager
            try:
                logger.info("Trying ChromeDriver with webdriver_manager")
                driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=chrome_options)
                return driver
            except Exception as e:
                errors.append(f"Failed with webdriver_manager: {str(e)}")
        except ImportError:
            errors.append("webdriver_manager not installed")
    
    # Method 4: Let Selenium find ChromeDriver in PATH
    try:
        logger.info("Trying ChromeDriver from system PATH")
        driver = webdriver.Chrome(options=chrome_options)
        return driver
    except Exception as e:
        errors.append(f"Failed with system PATH: {str(e)}")
    
    # If all methods fail, raise exception with all errors
    error_message = "Failed to initialize ChromeDriver. Errors:\n" + "\n".join(errors)
    logger.error(error_message)
    raise WebDriverException(error_message)

if __name__ == "__main__":
    # Configure basic logging
    logging.basicConfig(level=logging.INFO,
                        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    
    # Test the setup function
    try:
        logger.info("Testing Chrome WebDriver setup...")
        driver = setup_chrome_driver()
        logger.info("Chrome WebDriver initialized successfully")
        driver.get("https://www.google.com")
        logger.info(f"Page title: {driver.title}")
        driver.quit()
    except Exception as e:
        logger.error(f"Test failed: {str(e)}")
