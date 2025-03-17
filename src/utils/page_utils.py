"""
Utility functions for page fetching, scrolling, and other common browser interactions.
"""

import time
from selenium import webdriver
from typing import Optional
import logging

def fetch_page(driver: webdriver.Chrome, url: str, initial_wait: int = 3, scroll_count: int = 3, scroll_wait: int = 1) -> Optional[str]:
    """
    Fetch a page and scroll through it to load dynamic content.
    
    Args:
        driver: Selenium WebDriver instance
        url: URL to fetch
        initial_wait: Time to wait after initial page load (seconds)
        scroll_count: Number of scroll attempts
        scroll_wait: Time to wait between scrolls (seconds)
        
    Returns:
        Page HTML source if successful, None otherwise
    """
    try:
        driver.get(url)
        time.sleep(initial_wait)  # Initial load wait
        
        # Scroll logic
        last_height = driver.execute_script("return document.body.scrollHeight")
        for _ in range(scroll_count):
            driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
            time.sleep(scroll_wait)
            new_height = driver.execute_script("return document.body.scrollHeight")
            if new_height == last_height:
                break
            last_height = new_height
            
        return driver.page_source
    except Exception as e:
        logging.error(f"Error fetching page {url}: {e}")
        return None

def scroll_page(driver, max_attempts=5):
    """
    Scroll page until no new content is loaded.
    
    Args:
        driver: WebDriver instance
        max_attempts: Maximum attempts without new content before stopping.
                     Use -1 for unlimited scrolling until no new content
    """
    last_height = 0
    same_height_count = 0
    total_scrolls = 0
    
    # Convert -1 to a large number for unlimited scrolling
    effective_max = 10000 if max_attempts == -1 else max_attempts
    
    # Reduce wait time to avoid timeouts
    scroll_wait = 1  # Reduced from 2 seconds to 1 second
    
    while (same_height_count < 3 and (max_attempts == -1 or total_scrolls < effective_max)):
        driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
        time.sleep(scroll_wait)  # Reduced wait time
        
        new_height = driver.execute_script("return document.body.scrollHeight")
        
        if new_height == last_height:
            same_height_count += 1
            if same_height_count >= 3:  # Always stop after 3 consecutive no-changes
                logging.info(f"No new content after {total_scrolls} scrolls")
                break
                
            # Try scroll up/down to trigger lazy loading
            logging.debug("Trying scroll up/down to trigger content load")
            driver.execute_script(f"window.scrollTo(0, {new_height * 0.5});")
            time.sleep(1)
            driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
            time.sleep(1)
        else:
            same_height_count = 0
            total_scrolls += 1
            logging.debug(f"New content loaded at scroll {total_scrolls} (height: {new_height})")
            
        last_height = new_height

def click_load_more(driver, button_selectors=None, wait_time=3):
    """
    Click a "Load More" button using various selection strategies.
    
    Args:
        driver: Selenium WebDriver instance
        button_selectors: List of XPATH or CSS selectors to try
        wait_time: Time to wait after clicking (seconds)
        
    Returns:
        True if button was clicked successfully, False otherwise
    """
    from selenium.webdriver.common.by import By
    from selenium.webdriver.support.ui import WebDriverWait
    from selenium.webdriver.support import expected_conditions as EC
    
    if button_selectors is None:
        # Default to common "load more" button patterns
        button_selectors = [
            "//button[contains(@class, 'load-more')]", 
            "//button[contains(@class, 'btn-load')]",
            "//a[contains(@class, 'load-more')]",
            "//div[contains(@class, 'load-more')]//button"
        ]
    
    # Try each selector until we find a button
    button = None
    for selector in button_selectors:
        try:
            button = WebDriverWait(driver, 5).until(
                EC.presence_of_element_located((
                    By.XPATH if selector.startswith('//') else By.CSS_SELECTOR, 
                    selector
                ))
            )
            if button and button.is_displayed():
                break
        except:
            continue
    
    if not button:
        logging.debug("Load more button not found with any selector")
        return False
        
    # Scroll button into view with offset
    driver.execute_script("""
        arguments[0].scrollIntoView();
        window.scrollBy(0, -100);
    """, button)
    time.sleep(1)
    
    # Try multiple click methods
    try:
        # Try regular click
        button.click()
    except:
        try:
            # Try JavaScript click
            driver.execute_script("arguments[0].click();", button)
        except:
            # Final attempt: dispatch click event
            driver.execute_script("""
                var event = new MouseEvent('click', {
                    bubbles: true,
                    cancelable: true,
                    view: window
                });
                arguments[0].dispatchEvent(event);
            """, button)
            
    time.sleep(wait_time)  # Wait for content to load
    return True
