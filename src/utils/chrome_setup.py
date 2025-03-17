"""
Chrome and ChromeDriver setup utilities.
This module handles the setup of the Chrome WebDriver in a cross-platform manner.
"""

import os
import sys
import platform
import logging
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options

logger = logging.getLogger(__name__)

def detect_platform():
    """Detect the current platform and return a standardized string."""
    system = platform.system().lower()
    if system == "darwin":
        return "mac"
    elif system == "linux":
        return "linux"
    else:
        logger.warning(f"Unknown platform: {system}, defaulting to Linux")
        return "linux"

def get_chromedriver_path():
    """Get the ChromeDriver path based on platform."""
    platform_name = detect_platform()
    
    if platform_name == "mac":
        # On macOS, try multiple potential locations
        potential_paths = [
            "/usr/local/bin/chromedriver",
            os.path.expanduser("~/chromedriver"),
            os.path.expanduser("~/Downloads/chromedriver")
        ]
        
        # First check if ChromeDriver is in PATH
        import shutil
        chromedriver_in_path = shutil.which("chromedriver")
        if chromedriver_in_path:
            logger.info(f"Found ChromeDriver in PATH: {chromedriver_in_path}")
            return chromedriver_in_path
        
        # Then check known locations
        for path in potential_paths:
            if os.path.isfile(path):
                logger.info(f"Found ChromeDriver at: {path}")
                return path
                
        # If not found, check for homebrew installation
        brew_path = "/opt/homebrew/bin/chromedriver"
        if os.path.isfile(brew_path):
            logger.info(f"Found ChromeDriver at Homebrew location: {brew_path}")
            return brew_path
            
        # Nothing found, return None and let ChromeDriver's automatic detection work
        logger.warning("ChromeDriver not found in known locations, using auto-detection")
        return None
        
    elif platform_name == "windows":
        # On Windows, try standard installation paths
        potential_paths = [
            "C:\\Program Files\\chromedriver.exe",
            "C:\\Program Files\\chromedriver-win64\\chromedriver.exe",
            "C:\\chromedriver.exe",
            os.path.join(os.environ.get("USERPROFILE", ""), "Downloads", "chromedriver.exe")
        ]
        
        for path in potential_paths:
            if os.path.isfile(path):
                logger.info(f"Found ChromeDriver at: {path}")
                return path
                
        logger.warning("ChromeDriver not found in known Windows locations, using auto-detection")
        return None
        
    elif platform_name == "linux":
        # On Linux, try standard paths
        potential_paths = [
            "/usr/local/bin/chromedriver",
            "/usr/bin/chromedriver",
            os.path.expanduser("~/chromedriver")
        ]
        
        for path in potential_paths:
            if os.path.isfile(path):
                logger.info(f"Found ChromeDriver at: {path}")
                return path
                
        logger.warning("ChromeDriver not found in known Linux locations, using auto-detection")
        return None

def setup_chrome_driver(**kwargs):
    """Set up Chrome WebDriver with appropriate options and return it."""
    options = Options()
    if kwargs.get("headless", True):
        options.add_argument("--headless")  # Run in headless mode (no GUI)
    if kwargs.get("disable_images", False):
        prefs = {"profile.managed_default_content_settings.images": 2}
        options.add_experimental_option("prefs", prefs)
    if kwargs.get("random_user_agent", False):
        options.add_argument("user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/58.0.3029.110 Safari/537.3")
    options.add_argument("--no-sandbox")  # Bypass OS security model, required on some systems
    options.add_argument("--disable-dev-shm-usage")  # Overcome limited resource problems
    options.add_argument("--disable-gpu")  # Applicable to windows os only
    options.add_argument("--disable-extensions")  # Disable extensions for better stability
    options.add_argument("--window-size=1920,1080")  # Set window size
    options.add_argument("--disable-popup-blocking")  # Disable pop-up blocking
    
    # Get ChromeDriver path
    chromedriver_path = get_chromedriver_path()
    
    try:
        if chromedriver_path:
            service = Service(executable_path=chromedriver_path)
            driver = webdriver.Chrome(service=service, options=options)
        else:
            # Let Selenium try to automatically find ChromeDriver
            driver = webdriver.Chrome(options=options)
        
        # Set page load timeout
        driver.set_page_load_timeout(30)
        logger.info("Chrome WebDriver set up successfully")
        return driver
    except Exception as e:
        logger.error(f"Failed to set up Chrome WebDriver: {e}")
        # More detailed diagnostic info
        logger.error(f"Chrome options: {options.arguments}")
        logger.error(f"ChromeDriver path: {chromedriver_path}")
        logger.error(f"Platform: {platform.system()} {platform.release()}")
        logger.error(f"Python version: {sys.version}")
        raise

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
