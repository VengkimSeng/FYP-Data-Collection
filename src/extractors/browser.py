"""
Browser utilities for the article crawler.
"""

from selenium import webdriver
from selenium.webdriver.chrome.service import Service

def get_chrome_options():
    """Configure Chrome options with anti-detection measures."""
    options = webdriver.ChromeOptions()
    options.add_argument("--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36")
    options.add_argument("--disable-blink-features=AutomationControlled")  # Prevent bot detection
    options.add_argument("--headless")  # Run in headless mode
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-gpu")
    # Additional anti-detection measures
    options.add_experimental_option("excludeSwitches", ["enable-automation"])
    options.add_experimental_option("useAutomationExtension", False)
    options.add_argument("--disable-extensions")
    return options

def create_driver():
    """Create a configured Chrome WebDriver."""
    service = Service("C:\\Program Files\\chromedriver-win64\\chromedriver.exe")
    options = get_chrome_options()
    return webdriver.Chrome(service=service, options=options)
