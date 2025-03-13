"""
Scraper for Sabay News website.
"""

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
def scrape_sabay(url, category):
    """
    Scrape articles from Sabay News website.
    
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
            log_scrape_status(f"Scraping Sabay: {url}")
            driver.get(url)
            log_scrape_status(f"Selenium opened URL successfully: {url}")
            print(f"Page title: {driver.title}")
            
            # Wait for title to load
            try:
                title_element = WebDriverWait(driver, MAX_WAIT_TIME).until(
                    EC.presence_of_element_located((By.CSS_SELECTOR, "div.title.detail p"))
                )
                title = title_element.text.strip()
            except TimeoutException:
                print(f"{Fore.RED}[ERROR] Title element timeout for {url}{Style.RESET_ALL}")
                title = "Title Not Found"
            
            # Wait for content to load
            try:
                content_div = WebDriverWait(driver, MAX_WAIT_TIME).until(
                    EC.presence_of_element_located((By.CSS_SELECTOR, "div.detail.content-detail"))
                )
                
                # Get all text paragraphs, excluding ads and other elements
                paragraphs = []
                for p in content_div.find_elements(By.TAG_NAME, "p"):
                    # Skip paragraphs that are part of ads
                    if not any(ad_class in p.get_attribute("class") or "ads" in p.get_attribute("class") 
                            for ad_class in ["hide-line-spacing", "advertise-title"]):
                        text = p.text.strip()
                        if text:  # Only add non-empty paragraphs
                            paragraphs.append(text)
                
                content = "\n".join(paragraphs)
            except TimeoutException:
                print(f"{Fore.RED}[ERROR] Content element timeout for {url}{Style.RESET_ALL}")
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
                print(f"{Fore.GREEN}✓ Saved Sabay article: {title[:50]}...{Style.RESET_ALL}")
                return article_data
            else:
                raise Exception(f"Failed to extract complete article. Title found: {title != 'Title Not Found'}, Content found: {content != 'Content Not Found'}")

        except Exception as e:
            log_scrape_status(f"{Fore.RED}[ERROR] Failed to scrape Sabay {url}: {str(e)}{Style.RESET_ALL}")
            # Save page source for debugging
            try:
                if driver:
                    with open(f"debug_sabay_{int(time.time())}.html", "w", encoding="utf-8") as f:
                        f.write(driver.page_source)
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
SCRAPER_MAP["https://news.sabay.com.kh"] = scrape_sabay
