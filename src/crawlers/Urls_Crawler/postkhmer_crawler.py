from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from bs4 import BeautifulSoup
from urllib.parse import urljoin, urlparse
import time
import os
import sys
import logging
import warnings
import urllib3
import json

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# Suppress the urllib3 warning about OpenSSL
warnings.filterwarnings("ignore", category=urllib3.exceptions.NotOpenSSLWarning)

# Add parent directory to sys.path to import chrome_setup module
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from src.utils.chrome_setup import setup_chrome_driver

# Import the url_saver module
from src.utils.url_saver import save_urls_to_file

# Import URLManager
from src.crawlers.url_manager import URLManager

def setup_selenium():
    """Setup Selenium WebDriver with headless mode."""
    try:
        # Use the chrome_setup module to get a configured WebDriver
        logger.info("Setting up Selenium WebDriver...")
        driver = setup_chrome_driver(
            headless=True,
            disable_images=True,
            random_user_agent=True
        )
        logger.info("WebDriver setup successful")
        return driver
    except Exception as e:
        logger.error(f"Error setting up WebDriver: {e}")
        raise

def scroll_and_click(driver, category):
    """Scroll to the load more button and click it."""
    try:
        # Try different strategies to find the load more button
        wait = WebDriverWait(driver, 15)  # Wait up to 15 seconds
        
        # Strategy 1: Try with category in button text (most specific)
        try:
            xpath = f"//div[contains(@class, 'load-more')]//button[contains(@class, 'btn-load') and contains(text(), '{category}')]"
            load_more_btn = wait.until(
                EC.element_to_be_clickable((By.XPATH, xpath))
            )
            logger.info(f"Found button with category text: {category}")
        except:
            # Strategy 2: Try any btn-load inside load-more div
            try:
                xpath = "//div[contains(@class, 'load-more')]//button[contains(@class, 'btn-load')]"
                load_more_btn = wait.until(
                    EC.element_to_be_clickable((By.XPATH, xpath))
                )
                logger.info("Found button with class btn-load")
            except:
                # Strategy 3: Try with CSS selector
                try:
                    css_selector = "div.load-more button.btn-load"
                    load_more_btn = wait.until(
                        EC.element_to_be_clickable((By.CSS_SELECTOR, css_selector))
                    )
                    logger.info("Found button with CSS selector")
                except:
                    # Strategy 4: Just try to find any button with class btn-load
                    load_more_btn = wait.until(
                        EC.element_to_be_clickable((By.CLASS_NAME, "btn-load"))
                    )
                    logger.info("Found button with simple class name")
        
        # Scroll to button - ensure it's in view
        driver.execute_script("arguments[0].scrollIntoView({block: 'center', behavior: 'smooth'});", load_more_btn)
        time.sleep(2)  # Let the page settle after scrolling
        
        # Print button text for debugging
        button_text = load_more_btn.text
        logger.info(f"Button text: '{button_text}'")
        
        # Click button using JavaScript (more reliable than direct click)
        logger.info("Clicking 'load more' button")
        driver.execute_script("arguments[0].click();", load_more_btn)
        
        # Wait for new content to load
        time.sleep(5)  # Increased wait time to ensure content loads
        return True
    except Exception as e:
        logger.error(f"Error clicking load more button: {e}")
        
        # Fallback - try to find the button by JavaScript directly
        try:
            logger.info("Trying fallback JavaScript button click")
            # Try to click any button with class btn-load
            driver.execute_script("document.querySelector('.btn-load').click();")
            time.sleep(5)
            return True
        except:
            logger.error("Fallback JavaScript click also failed")
            return False

def extract_article_urls(soup, base_url):
    """Extract article URLs from the more-content section."""
    urls = set()
    
    # Log the structure to debug
    more_content = soup.find("div", class_="more-contents")
    if more_content:
        logger.info("Found more-contents div")
        article_items = more_content.find_all("div", class_="more-item")
        logger.info(f"Found {len(article_items)} article items")
        
        # Process each article item
        for item in article_items:
            # Get the main article link (heading link)
            more_text = item.find("div", class_="more-text")
            if more_text:
                article_link = more_text.find("a")
                if article_link and "href" in article_link.attrs:
                    href = article_link["href"]
                    full_url = urljoin(base_url, href)
                    urls.add(full_url)
                    
            # Also check the image link which sometimes differs
            img_container = item.find("div", class_="more-img")
            if img_container:
                img_link = img_container.find("a")
                if img_link and "href" in img_link.attrs:
                    href = img_link["href"]
                    full_url = urljoin(base_url, href)
                    urls.add(full_url)
    else:
        # If more-contents not found, try alternative selectors
        logger.warning("more-contents div not found, trying alternate selectors")
        
        # Try to extract URLs from article-news section if it exists
        article_news = soup.find("div", class_="article-news")
        if article_news:
            logger.info("Found article-news div")
            for a_tag in article_news.find_all("a", href=True):
                href = a_tag["href"]
                if href and not href == "#" and not href.startswith("javascript"):
                    full_url = urljoin(base_url, href)
                    urls.add(full_url)
        
        # Extract all article links from the page as a fallback
        for a_tag in soup.find_all("a", href=True):
            href = a_tag["href"]
            # Filter links to make sure they're articles
            if href and href.startswith(("/politics/", "/business/", "/national/", "/sport/", "/lifestyle/", "/world/")):
                full_url = urljoin(base_url, href)
                urls.add(full_url)
    
    return urls

def scrape_page_content(driver, base_url, category, url_manager):
    """Scrape URLs from the page, handling button clicks to load more content."""
    visited_urls = set()  # Store unique URLs
    click_attempts = 0
    max_attempts = 30  # Limit clicks to avoid infinite loops
    consecutive_failures = 0
    max_consecutive_failures = 3  # Stop after this many consecutive failures
    
    # Initial page load
    logger.info("Extracting initial URLs")
    soup = BeautifulSoup(driver.page_source, "html.parser")
    initial_urls = extract_article_urls(soup, base_url)
    visited_urls.update(initial_urls)
    
    # Add initial URLs to URL manager
    if initial_urls:
        added = url_manager.add_urls(category, initial_urls)
        logger.info(f"Initial load: Added {added} new article URLs")
    
    # Continue clicking load more until conditions are met
    while click_attempts < max_attempts and consecutive_failures < max_consecutive_failures:
        # Try to click the load more button
        if scroll_and_click(driver, category):
            # Reset consecutive failures counter on success
            consecutive_failures = 0
        else:
            # Increment failures counter
            consecutive_failures += 1
            logger.warning(f"Failed to click load more button ({consecutive_failures}/{max_consecutive_failures})")
            if consecutive_failures >= max_consecutive_failures:
                logger.info("Maximum consecutive failures reached, stopping")
                break
        
        # Increment click counter
        click_attempts += 1
        
        # Parse the updated page
        soup = BeautifulSoup(driver.page_source, "html.parser")
        previous_count = len(visited_urls)
        
        # Extract new URLs
        new_urls = extract_article_urls(soup, base_url)
        visited_urls.update(new_urls)
        current_count = len(visited_urls)
        
        # Log progress and add to URL manager if we found new URLs
        if current_count > previous_count:
            new_urls_to_add = set()
            for url in new_urls:
                if url not in visited_urls:
                    new_urls_to_add.add(url)
            
            if new_urls_to_add:
                added = url_manager.add_urls(category, new_urls_to_add)
                logger.info(f"Click #{click_attempts}: Added {added} new URLs to URL manager")
        
        logger.info(f"Click #{click_attempts}: Found {current_count} total URLs (+{current_count - previous_count} new)")
        
        # If no new URLs were found, we might have reached the end
        if current_count == previous_count:
            consecutive_failures += 1
            logger.warning(f"No new URLs found after clicking ({consecutive_failures}/{max_consecutive_failures})")
            if consecutive_failures >= max_consecutive_failures:
                logger.info("Maximum consecutive failures with no new content reached, stopping")
                break
        
        # Pause between clicks
        time.sleep(3)

    logger.info(f"Scraping completed for {base_url}. Total URLs: {len(visited_urls)}")
    
    # Return the collected URLs
    return visited_urls

def filter_postkhmer_urls(urls):
    """Filter PostKhmer URLs based on specific criteria."""
    filtered_urls = []
    
    for url in urls:
        # Parse URL to analyze components
        parsed = urlparse(url)
        
        # Basic validation
        if not parsed.netloc or not parsed.scheme:
            continue
            
        # Make sure it's from postkhmer.com
        if "postkhmer.com" not in parsed.netloc:
            continue
            
        # Filter out non-article pages
        path = parsed.path.lower()
        if any(exclude in path for exclude in [
            "/search", "/tag/", "/category/", "/author/", 
            "/page/", "/about", "/contact", "/privacy", 
            "/terms", "/subscribe", "/login", "/register"
        ]):
            continue
            
        # Ensure it's a content page
        if not path.startswith(("/politics/", "/business/", "/national/", 
                               "/sport/", "/lifestyle/", "/world/", 
                               "/financial/")):
            continue
            
        # Additional check for article pages (they usually have a numeric ID)
        if path.count('/') < 2:  # Need at least /category/article-title
            continue
            
        # Keep only HTML pages
        if path.endswith((".jpg", ".jpeg", ".png", ".gif", ".pdf", ".mp3", ".mp4")):
            continue
            
        # Add to filtered list
        filtered_urls.append(url)
    
    logger.info(f"Filtered {len(filtered_urls)} URLs out of {len(urls)} total URLs")
    return filtered_urls

def main():
    # List of URLs to scrape
    urls_to_scrape = [
        "https://www.postkhmer.com/politics",
        "https://www.postkhmer.com/business",
        "https://www.postkhmer.com/financial",
        "https://www.postkhmer.com/sport",
        # Add more categories as needed
        "https://www.postkhmer.com/national",
        "https://www.postkhmer.com/lifestyle",
        "https://www.postkhmer.com/world"
    ]

    # Use standard output directory
    output_dir = "output/urls"
    os.makedirs(output_dir, exist_ok=True)
    logger.info(f"Output directory: {output_dir}")

    # Initialize URL manager with the standard output directory
    url_manager = URLManager(output_dir, "postkhmer")

    try:
        driver = setup_selenium()
        for url in urls_to_scrape:
            logger.info(f"Scraping category: {url}")
            # Extract category name from URL
            category = url.split("/")[-1]
            
            driver.get(url)  # Load the website
            logger.info(f"Loaded URL: {url}")
            time.sleep(5)  # Wait for the page to load completely
            
            # Scrape content for the current URL
            urls = scrape_page_content(driver, url, category, url_manager)
            
            # Filter the URLs
            filtered_urls = filter_postkhmer_urls(list(urls))
            
            # Add filtered URLs to URL manager
            added = url_manager.add_urls(category, filtered_urls)
            logger.info(f"Added {added} filtered URLs from {url}")
    except Exception as e:
        logger.error(f"An error occurred: {e}", exc_info=True)
    finally:
        if 'driver' in locals():
            logger.info("Closing WebDriver")
            driver.quit()
        
        # Save final results
        if 'url_manager' in locals():
            results = url_manager.save_final_results()
            logger.info(f"Total URLs saved: {sum(results.values())}")

if __name__ == "__main__":
    main()
