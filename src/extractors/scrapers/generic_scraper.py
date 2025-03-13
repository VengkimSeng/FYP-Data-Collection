"""
Generic scraper for websites with similar structures.
"""

import threading
import time
import traceback
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException
from colorama import Fore, Style

from ..browser import create_driver
from ..utils import retry_on_exception, is_scraped
from ..logger import log_scrape_status, log_debug, log_category_progress, log_category_error
from ..storage import save_article_data
from ..config import MAX_WAIT_TIME

@retry_on_exception()
def generic_scrape(url, category, title_selector, content_selector, is_id=False):
    """Generic scraper for websites with similar structure."""
    # Check if already scraped
    if is_scraped(category, url):
        log_scrape_status(f"{Fore.YELLOW}[SKIPPED] Already scraped: {url}{Style.RESET_ALL}")
        log_category_progress(category, url, "SKIPPED: URL already scraped", is_start=True, is_end=True)
        return None

    driver = None
    html_debug_file = None
    try:
        log_scrape_status(f"🔍 Setting up Chrome for {url}")
        log_category_progress(category, url, "Setting up Chrome driver")
        driver = create_driver()

        try:
            log_scrape_status(f"🔍 Navigating to: {url}")
            driver.get(url)
            log_scrape_status(f"✅ Page loaded for: {url}")
            print(f"Page title: {driver.title}")
            log_scrape_status(f"📄 Page title: {driver.title}")
            log_scrape_status(f"{Fore.CYAN}[DEBUG] Using selectors - Title: {title_selector}, Content: {content_selector}{Style.RESET_ALL}")
            log_category_progress(category, url, f"Navigating to URL")
            log_category_progress(category, url, f"Using selectors - Title: {title_selector}, Content: {content_selector}")
            
            # Wait for title to load with heartbeat
            try:
                log_debug(f"Starting title extraction for: {url}")
                log_scrape_status(f"🔍 Searching for title using: {title_selector}")
                log_category_progress(category, url, f"Searching for title using: {title_selector}")
                
                # Use an event to signal when to stop the heartbeat
                title_stop_event = threading.Event()
                
                def title_heartbeat():
                    elapsed = 0
                    while not title_stop_event.is_set() and elapsed < MAX_WAIT_TIME:
                        print(f"Waiting for title... {elapsed}s elapsed")
                        time.sleep(5)
                        elapsed += 5
                    log_debug(f"Title heartbeat thread ending. Stop event set: {title_stop_event.is_set()}")
                
                heartbeat_thread = threading.Thread(target=title_heartbeat)
                heartbeat_thread.daemon = True
                heartbeat_thread.start()
                
                log_debug(f"Waiting for title element using selector: {title_selector}")
                if not is_id:
                    title_element = WebDriverWait(driver, MAX_WAIT_TIME).until(
                        EC.presence_of_element_located((By.CSS_SELECTOR, title_selector))
                    )
                else:
                    title_element = WebDriverWait(driver, MAX_WAIT_TIME).until(
                        EC.presence_of_element_located((By.TAG_NAME, title_selector))
                    )
                
                # Signal the heartbeat thread to stop
                title_stop_event.set()
                log_debug("Title element found, stopping heartbeat thread")
                
                title = title_element.text.strip()
                log_scrape_status(f"✅ Title found: {title[:50]}...")
                log_category_progress(category, url, f"Title found: {title[:50]}...")
            except TimeoutException:
                log_scrape_status(f"{Fore.RED}❌ [ERROR] Title element timeout for {url}{Style.RESET_ALL}")
                log_category_progress(category, url, f"ERROR: Title element timeout for {url}")
                title = "Title Not Found"
            finally:
                # Ensure we signal the thread to stop
                if 'title_stop_event' in locals():
                    title_stop_event.set()
                    log_debug("Title heartbeat stop event set")
            
            # Wait for content to load with heartbeat
            try:
                log_debug(f"Starting content extraction for: {url}")
                log_scrape_status(f"🔍 Searching for content using: {content_selector}")
                log_category_progress(category, url, f"Searching for content using: {content_selector}")
                content_stop_event = threading.Event()
                
                def content_heartbeat():
                    elapsed = 0
                    while not content_stop_event.is_set() and elapsed < MAX_WAIT_TIME:
                        print(f"Waiting for content... {elapsed}s elapsed")
                        time.sleep(5)
                        elapsed += 5
                    log_debug(f"Content heartbeat thread ending. Stop event set: {content_stop_event.is_set()}")
                
                heartbeat_thread = threading.Thread(target=content_heartbeat)
                heartbeat_thread.daemon = True
                heartbeat_thread.start()
                
                log_debug(f"Waiting for content element using selector: {content_selector} (is_id={is_id})")
                if is_id:
                    content_div = WebDriverWait(driver, MAX_WAIT_TIME).until(
                        EC.presence_of_element_located((By.ID, content_selector))
                    )
                else:
                    content_div = WebDriverWait(driver, MAX_WAIT_TIME).until(
                        EC.presence_of_element_located((By.CLASS_NAME, content_selector))
                    )
                
                # Signal the heartbeat thread to stop
                content_stop_event.set()
                log_debug("Content element found, stopping heartbeat thread")
                
                log_debug("Extracting text from paragraphs")
                paragraphs = [p.text.strip() for p in content_div.find_elements(By.TAG_NAME, "p")]
                log_debug(f"Found {len(paragraphs)} paragraphs")
                content = "\n".join(paragraphs)
                log_scrape_status(f"✅ Content found: {len(content)} characters")
                log_category_progress(category, url, f"Content found: {len(content)} characters")
            except TimeoutException:
                log_scrape_status(f"{Fore.RED}❌ [ERROR] Content element timeout for {url}{Style.RESET_ALL}")
                log_category_progress(category, url, f"ERROR: Content element timeout for {url}")
                content = "Content Not Found"
            finally:
                # Ensure we signal the thread to stop
                if 'content_stop_event' in locals():
                    content_stop_event.set()
                    log_debug("Content heartbeat stop event set")

            log_debug(f"Checking content validity - Title found: {title != 'Title Not Found'}, Content found: {content != 'Content Not Found'}")
            log_scrape_status(f"📋 Validation - Title: {'✅' if title != 'Title Not Found' else '❌'}, Content: {'✅' if content != 'Content Not Found' else '❌'}")
            log_category_progress(category, url, f"Validation - Title: {'✅' if title != 'Title Not Found' else '❌'}, Content: {'✅' if content != 'Content Not Found' else '❌'}")
            
            if title != "Title Not Found" and content != "Content Not Found":
                # Include title, content, URL, and category in article data
                article_data = {
                    "title": title,
                    "content": content,
                    "url": url,
                    "category": category
                }

                log_debug(f"Preparing to save article data for: {url}")
                log_scrape_status(f"💾 Saving article for: {url}")
                log_category_progress(category, url, f"Saving article data")
                
                save_article_data(category, article_data, url)  # Pass URL separately
                
                print(f"{Fore.GREEN}✓ Saved article: {title[:50]}...{Style.RESET_ALL}")
                log_debug(f"Returning article data for: {url}")
                log_scrape_status(f"✅ Article data ready for: {url}")
                log_category_progress(category, url, f"Article data ready")
                return article_data
            else:
                log_scrape_status(f"❌ Failed to extract complete article from: {url}")
                log_category_progress(category, url, f"ERROR: Failed to extract complete article from: {url}")
                raise Exception(f"Title or Content Not Found. Title found: {title != 'Title Not Found'}, Content found: {content != 'Content Not Found'}")

        except Exception as e:
            error_msg = f"Failed to scrape: {str(e)}"
            log_scrape_status(f"{Fore.RED}❌ [ERROR] {error_msg}{Style.RESET_ALL}")
            log_category_progress(category, url, f"ERROR: {error_msg}")
            
            # Save page source for debugging
            try:
                if driver:
                    log_debug(f"Saving debug HTML for failed URL: {url}")
                    html_debug_file = f"debug_generic_{int(time.time())}.html"
                    with open(html_debug_file, "w", encoding="utf-8") as f:
                        f.write(driver.page_source)
                    log_debug(f"Debug HTML saved to: {html_debug_file}")
                    log_category_progress(category, url, f"Debug HTML saved to: {html_debug_file}")
                    
                    # Log the error with HTML file reference
                    log_category_error(category, url, error_msg, html_debug_file)
            except Exception as debug_err:
                log_debug(f"Failed to save debug HTML: {str(debug_err)}")
                log_category_progress(category, url, f"Failed to save debug HTML: {str(debug_err)}")
                log_category_error(category, url, f"{error_msg}; Failed to save debug HTML: {str(debug_err)}")
            
            raise  # Re-raise for retry decorator
    finally:
        if driver:  # Check if driver exists before quitting
            try:
                log_debug(f"Attempting to quit driver for: {url}")
                log_category_progress(category, url, "Closing Chrome driver")
                driver.quit()
                log_debug(f"Driver successfully closed for: {url}")
            except Exception as driver_err:
                error_msg = f"Failed to close driver: {str(driver_err)}"
                log_scrape_status(f"{Fore.YELLOW}⚠️ [WARNING] {error_msg}{Style.RESET_ALL}")
                log_category_progress(category, url, f"WARNING: {error_msg}")
                log_category_error(category, url, error_msg, html_debug_file)
        log_scrape_status(f"🏁 Browser closed for: {url}. Ready for next URL.")
        log_category_progress(category, url, "Browser closed, ready for next URL", is_end=True)
