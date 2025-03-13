"""
Scraper for Radio Free Asia (RFA) website.
"""

import threading
import time
import random  # Add import for random delays
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException
from colorama import Fore, Style

from ..browser import create_driver
from ..utils import retry_on_exception, is_scraped
from ..logger import log_scrape_status
from ..storage import save_article_data
from ..config import SCRAPER_MAP, MAX_WAIT_TIME

@retry_on_exception()
def scrape_rfa(url, category):
    """
    Scrape articles from RFA website.
    
    Args:
        url: URL to scrape
        category: Category of the article
        
    Returns:
        Dict containing article data if successful, None otherwise
    """
    # Check if already scraped
    if is_scraped(category, url):
        log_scrape_status(f"{Fore.YELLOW}[SKIPPED] Already scraped: {url}{Style.RESET_ALL}")
        return None
        
    driver = None
    try:
        driver = create_driver()

        try:
            log_scrape_status(f"Scraping RFA: {url}")
            driver.get(url)
            log_scrape_status(f"Selenium opened URL successfully: {url}")
            print(f"Page title: {driver.title}")
            
            # Wait for h1 tag to load
            try:
                # Log heartbeat while waiting
                heartbeat_thread = threading.Thread(
                    target=lambda: [print(f"Waiting for title... {int(time.time() - start_time)}s elapsed") or time.sleep(5) 
                                for _ in range(int(MAX_WAIT_TIME/5))],
                    daemon=True
                )
                start_time = time.time()
                heartbeat_thread.start()
                
                title_element = WebDriverWait(driver, MAX_WAIT_TIME).until(
                    EC.presence_of_element_located((By.TAG_NAME, "h1"))
                )
                title = title_element.text.strip()
                log_scrape_status(f"Title found: {title[:50]}...")
            except TimeoutException:
                log_scrape_status(f"{Fore.RED}[ERROR] Title element timeout for {url}{Style.RESET_ALL}")
                title = "Title Not Found"
            
            # Wait for content to load with heartbeat
            try:
                start_time = time.time()
                heartbeat_thread = threading.Thread(
                    target=lambda: [print(f"Waiting for content... {int(time.time() - start_time)}s elapsed") or time.sleep(5) 
                                for _ in range(int(MAX_WAIT_TIME/5))],
                    daemon=True
                )
                heartbeat_thread.start()
                
                content_div = WebDriverWait(driver, MAX_WAIT_TIME).until(
                    EC.presence_of_element_located((By.ID, "storytext"))
                )
                content = "\n".join([p.text.strip() for p in content_div.find_elements(By.TAG_NAME, "p")])
                log_scrape_status(f"Content found: {len(content)} characters")
            except TimeoutException:
                log_scrape_status(f"{Fore.RED}[ERROR] Content element timeout for {url}{Style.RESET_ALL}")
                content = "Content Not Found"

            # Verify we have valid content
            if title != "Title Not Found" and content != "Content Not Found":
                # Include title, content, URL, and category in article data
                article_data = {
                    "title": title,
                    "content": content,
                    "url": url,
                    "category": category
                }

                save_article_data(category, article_data, url)
                print(f"{Fore.GREEN}✓ Saved RFA article: {title[:50]}...{Style.RESET_ALL}")
                return article_data
            else:
                raise Exception(f"Failed to extract complete article. Title found: {title != 'Title Not Found'}, Content found: {content != 'Content Not Found'}")

        except Exception as e:
            log_scrape_status(f"{Fore.RED}[ERROR] Error scraping RFA {url}: {str(e)}{Style.RESET_ALL}")
            # Save page source for debugging
            try:
                if driver:
                    with open(f"debug_rfa_{int(time.time())}.html", "w", encoding="utf-8") as f:
                        f.write(driver.page_source)
                    log_scrape_status(f"Saved debug HTML to debug_rfa_{int(time.time())}.html")
            except:
                pass
            raise  # Re-raise for retry decorator
    finally:
        if driver:
            try:
                driver.quit()
            except:
                log_scrape_status(f"{Fore.YELLOW}[WARNING] Failed to close driver properly for: {url}")
        log_scrape_status(f"Driver closed for: {url}. Moving to the next URL.")

# Register the scraper in the SCRAPER_MAP
SCRAPER_MAP["https://www.rfa.org"] = scrape_rfa
