import os
import json
import concurrent.futures
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from urllib.parse import urlparse
from selenium.common.exceptions import NoSuchElementException, TimeoutException, WebDriverException
import time
import threading
from colorama import Fore, Style, init
# Add imports for explicit waits
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
# Import for retry functionality
from functools import wraps
# Add imports for logging and animation
import logging
import datetime
import sys
import itertools
# Import for stack trace logging
import traceback
# Import for URL safe filenames
import re
import hashlib
# Import for command line argument parsing
import argparse

# Prevent TensorFlow Lite logs and disable GPU to avoid conflicts
os.environ["TF_CPP_MIN_LOG_LEVEL"] = "3"
os.environ["CUDA_VISIBLE_DEVICES"] = "-1"

# Initialize colorama for colored terminal output
init(autoreset=True)

# Configure logging
logging.basicConfig(
    filename="scraping_log.txt",
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
)

def log_scrape_status(message):
    timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    print(f"{timestamp} | {message}")
    logging.info(message)

# Loading animation flag and function
stop_loading = False

def loading_animation():
    while not stop_loading:  # Improved loop condition
        for c in ['|', '/', '-', '\\']:
            if stop_loading:
                return  # Exit immediately when flag is set
            sys.stdout.write(f'\r{Fore.CYAN}Scraping in progress... {c}{Style.RESET_ALL}')
            sys.stdout.flush()
            time.sleep(0.2)
    sys.stdout.write('\r')
    sys.stdout.flush()

# Global variables
CHECKPOINT_DIR = "output/checkpoint"  # Directory for checkpoint file
CHECKPOINT_FILE = os.path.join(CHECKPOINT_DIR, "checkpoint.json")
LOGS_DIR = "output/logs/Article"  # Base directory for logs
CATEGORY_LOGS_DIR = os.path.join(LOGS_DIR, "Category_Logs")  # Directory for category logs
CATEGORY_ERRORS_DIR = os.path.join(LOGS_DIR, "Category_Errors")  # Directory for category errors
success_count = 0
lock = threading.Lock()
# Configure maximum wait time and retry settings
MAX_WAIT_TIME = 40  # seconds
MAX_RETRIES = 3  # This value is now enforced for all functions
RETRY_DELAY = 20 # seconds
# Set input and output directories
INPUT_DIR = "output/urls"  # Directory containing URL JSON files
OUTPUT_DIR = "output/articles"  # Directory for saving scraped articles

# Enhanced retry decorator that enforces MAX_RETRIES globally
def retry_on_exception(max_retries=None, delay=None):
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            # Always use global MAX_RETRIES and RETRY_DELAY regardless of parameters
            retries = 0
            while retries < MAX_RETRIES:
                try:
                    return func(*args, **kwargs)
                except Exception as e:
                    retries += 1
                    if retries >= MAX_RETRIES:
                        log_scrape_status(f"{Fore.RED}[ERROR] Max retries reached ({MAX_RETRIES}) for {func.__name__}: {e}{Style.RESET_ALL}")
                        raise
                    log_scrape_status(f"{Fore.YELLOW}[RETRY] Attempt {retries}/{MAX_RETRIES} for {func.__name__}: {e}{Style.RESET_ALL}")
                    
                    # Try to forcefully restart WebDriver if it's a WebDriver issue
                    if "driver" in kwargs:
                        try:
                            kwargs["driver"].quit()
                        except:
                            pass
                    
                    time.sleep(RETRY_DELAY)
            return None
        return wrapper
    return decorator

# Load checkpoint data (tracks URLs that have been scraped)
def load_checkpoint():
    if os.path.exists(CHECKPOINT_FILE):
        try:
            with open(CHECKPOINT_FILE, "r", encoding="utf-8") as file:
                return json.load(file)
        except json.JSONDecodeError:
            print(f"{Fore.YELLOW}Warning: Checkpoint file corrupted, resetting...{Style.RESET_ALL}")
            return {}
    return {}

# Check if URL is already scraped
def is_scraped(category, url):
    checkpoint_data = load_checkpoint()
    return category in checkpoint_data and url in checkpoint_data[category]

# Add function to log debug messages with a distinctive prefix
def log_debug(message):
    log_scrape_status(f"{Fore.BLUE}[DEBUG] {message}{Style.RESET_ALL}")

# Save checkpoint progress - add more logging
def update_checkpoint(category, url):
    with lock:
        # Ensure checkpoint directory exists
        os.makedirs(CHECKPOINT_DIR, exist_ok=True)
        
        log_debug(f"Updating checkpoint for {category}: {url}")
        checkpoint_data = load_checkpoint()
        if category not in checkpoint_data:
            checkpoint_data[category] = []
        checkpoint_data[category].append(url)
        
        try:
            with open(CHECKPOINT_FILE, "w", encoding="utf-8") as file:
                json.dump(checkpoint_data, file, ensure_ascii=False, indent=4)
            log_debug(f"Checkpoint updated successfully: {CHECKPOINT_FILE}")
        except Exception as e:
            log_scrape_status(f"{Fore.RED}[ERROR] Failed to update checkpoint: {str(e)}{Style.RESET_ALL}")

# Get platform-compatible ChromeDriver path
def get_chromedriver_path():
    """Return the appropriate ChromeDriver path based on OS"""
    
    platform = sys.platform
    
    # Define possible ChromeDriver locations by platform
    if platform.startswith('win'):  # Windows
        possible_paths = [
            "C:\\Program Files\\chromedriver-win64\\chromedriver.exe"
        ]
    elif platform.startswith('darwin'):  # macOS
        possible_paths = [
            "/opt/homebrew/bin/chromedriver"
        ]
    elif platform.startswith('linux'):  # Linux
        possible_paths = [
            "/usr/bin/chromedriver",
            "/usr/local/bin/chromedriver",
            "./chromedriver"
        ]
    else:
        possible_paths = ["chromedriver"]
    
    # Check if ChromeDriver exists in any of the possible locations
    for path in possible_paths:
        if os.path.exists(path):
            log_scrape_status(f"{Fore.GREEN}[INFO] ChromeDriver found at: {path}{Style.RESET_ALL}")
            return path
    
    # If chromedriver not found in common locations, check if it's in PATH
    import shutil
    chromedriver_in_path = shutil.which("chromedriver")
    if (chromedriver_in_path):
        log_scrape_status(f"{Fore.GREEN}[INFO] ChromeDriver found in PATH: {chromedriver_in_path}{Style.RESET_ALL}")
        return chromedriver_in_path
    
    # If we get here, no ChromeDriver was found
    log_scrape_status(f"{Fore.RED}[ERROR] ChromeDriver not found. Please install ChromeDriver and ensure it's in PATH.{Style.RESET_ALL}")
    log_scrape_status(f"{Fore.YELLOW}[INFO] Download ChromeDriver from: https://chromedriver.chromium.org/downloads{Style.RESET_ALL}")
    log_scrape_status(f"{Fore.YELLOW}[INFO] Make sure it matches your Chrome version{Style.RESET_ALL}")
    
    # Try to use the selenium-manager as a last resort
    return "chromedriver"

# Setup Chrome options with enhanced anti-detection measures
def get_chrome_options():
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
    # Remove the problematic option that's causing errors
    # options.add_experimental_option("use_selenium_manager", True)
    return options

# Define scraping functions for each base URL
def scrape_btv(url, category):
    return generic_scrape(url, category, "h4.color", "font-size-detail.textview")

def scrape_postkhmer(url, category):
    return generic_scrape(url, category, "div.section-article-header h2", "article-text")

@retry_on_exception()  # No parameters here to ensure using global MAX_RETRIES
def scrape_rfa(url, category):
    driver = None
    try:
        chromedriver_path = get_chromedriver_path()
        log_scrape_status(f"Using ChromeDriver from: {chromedriver_path}")
        
        try:
            # Try with Service first
            service = Service(chromedriver_path)
            options = get_chrome_options()
            driver = webdriver.Chrome(service=service, options=options)
        except Exception as driver_init_error:
            log_scrape_status(f"{Fore.YELLOW}[WARNING] Failed to initialize ChromeDriver with explicit path. Trying alternative approach...{Style.RESET_ALL}")
            log_scrape_status(f"Error details: {str(driver_init_error)}")
            
            # Try alternative initialization without Service
            try:
                options = get_chrome_options()
                driver = webdriver.Chrome(options=options)
                log_scrape_status(f"{Fore.GREEN}[SUCCESS] ChromeDriver initialized using alternative method{Style.RESET_ALL}")
            except Exception as alt_error:
                log_scrape_status(f"{Fore.RED}[ERROR] Both initialization methods failed: {str(alt_error)}{Style.RESET_ALL}")
                raise Exception(f"Failed to initialize ChromeDriver: {str(alt_error)}")

        try:
            log_scrape_status(f"Scraping RFA: {url}")
            driver.get(url)
            log_scrape_status(f"Selenium opened URL successfully: {url}")
            print(f"Page title: {driver.title}")
            
            # Heartbeat log to detect stuck pages
            start_time = time.time()
            
            # Wait for h1 tag to load
            try:
                # Log heartbeat while waiting
                heartbeat_thread = threading.Thread(
                    target=lambda: [print(f"Waiting for title... {int(time.time() - start_time)}s elapsed") or time.sleep(5) 
                                for _ in range(int(MAX_WAIT_TIME/5))]
                )
                heartbeat_thread.daemon = True
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
            content = "Content Not Found"
            
            # First attempt: Try the standard storytext div
            try:
                start_time = time.time()
                heartbeat_thread = threading.Thread(
                    target=lambda: [print(f"Waiting for content (method 1)... {int(time.time() - start_time)}s elapsed") or time.sleep(5) 
                                for _ in range(int(MAX_WAIT_TIME/5))]
                )
                heartbeat_thread.daemon = True
                heartbeat_thread.start()
                
                content_div = WebDriverWait(driver, MAX_WAIT_TIME).until(
                    EC.presence_of_element_located((By.ID, "storytext"))
                )
                
                paragraphs = []
                # Try to get regular paragraphs first
                p_elements = content_div.find_elements(By.TAG_NAME, "p")
                if p_elements:
                    paragraphs = [p.text.strip() for p in p_elements]
                    
                # If we didn't get any paragraphs, look for p.c-paragraph elements
                if not paragraphs:
                    log_scrape_status(f"{Fore.YELLOW}[WARNING] No standard paragraphs found, looking for p.c-paragraph elements...{Style.RESET_ALL}")
                    p_elements = content_div.find_elements(By.CSS_SELECTOR, "p.c-paragraph")
                    if p_elements:
                        paragraphs = [p.text.strip() for p in p_elements]
                
                if paragraphs:
                    content = "\n".join(paragraphs)
                    log_scrape_status(f"Content found: {len(content)} characters")
                else:
                    log_scrape_status(f"{Fore.YELLOW}[WARNING] No paragraphs found in storytext div{Style.RESET_ALL}")
            except TimeoutException:
                log_scrape_status(f"{Fore.YELLOW}[WARNING] Storytext div not found, trying alternative method...{Style.RESET_ALL}")
            except Exception as e:
                log_scrape_status(f"{Fore.YELLOW}[WARNING] Error extracting content from storytext: {str(e)}{Style.RESET_ALL}")
            
            # Second attempt: Try looking for p.c-paragraph elements directly if content is still not found
            if content == "Content Not Found":
                try:
                    log_scrape_status(f"{Fore.YELLOW}[INFO] Trying alternative content extraction method...{Style.RESET_ALL}")
                    
                    # Wait for any paragraph with c-paragraph class to appear
                    start_time = time.time()
                    heartbeat_thread = threading.Thread(
                        target=lambda: [print(f"Waiting for content (method 2)... {int(time.time() - start_time)}s elapsed") or time.sleep(5) 
                                    for _ in range(int(MAX_WAIT_TIME/5))]
                    )
                    heartbeat_thread.daemon = True
                    heartbeat_thread.start()
                    
                    # Try to find the article content container using different possible selectors
                    try:
                        # First try: Look for a specific article container
                        article_element = WebDriverWait(driver, 10).until(
                            EC.presence_of_element_located((By.CSS_SELECTOR, "div.articleContent, div.page-content, div.c-heroarea, div.o-body"))
                        )
                        log_scrape_status(f"{Fore.GREEN}[SUCCESS] Found article container element{Style.RESET_ALL}")
                    except:
                        # Second try: Just search the whole document
                        log_scrape_status(f"{Fore.YELLOW}[WARNING] No article container found, searching whole document...{Style.RESET_ALL}")
                        article_element = driver.find_element(By.TAG_NAME, "body")
                    
                    # Look for paragraphs with c-paragraph class
                    c_paragraphs = article_element.find_elements(By.CSS_SELECTOR, "p.c-paragraph")
                    if c_paragraphs:
                        log_scrape_status(f"{Fore.GREEN}[SUCCESS] Found {len(c_paragraphs)} p.c-paragraph elements{Style.RESET_ALL}")
                        paragraphs = [p.text.strip() for p in c_paragraphs]
                        content = "\n".join(paragraphs)
                        log_scrape_status(f"Content found: {len(content)} characters using alternative method")
                    else:
                        # Last resort: try to get any paragraph content
                        log_scrape_status(f"{Fore.YELLOW}[WARNING] No c-paragraph elements found, trying any paragraphs...{Style.RESET_ALL}")
                        all_paragraphs = article_element.find_elements(By.TAG_NAME, "p")
                        if all_paragraphs:
                            paragraphs = [p.text.strip() for p in all_paragraphs if p.text.strip()]
                            if paragraphs:
                                content = "\n".join(paragraphs)
                                log_scrape_status(f"Content found: {len(content)} characters using any paragraph elements")
                
                except Exception as e:
                    log_scrape_status(f"{Fore.RED}[ERROR] Alternative content extraction failed: {str(e)}{Style.RESET_ALL}")
                    # Save page source for detailed debugging
                    try:
                        debug_file = f"debug_rfa_detailed_{int(time.time())}.html"
                        with open(debug_file, "w", encoding="utf-8") as f:
                            f.write(driver.page_source)
                        log_scrape_status(f"{Fore.YELLOW}[INFO] Page source saved to {debug_file} for debugging{Style.RESET_ALL}")
                    except:
                        pass
            
            # Third attempt: If still no content, try a more generic approach
            if content == "Content Not Found":
                try:
                    log_scrape_status(f"{Fore.YELLOW}[INFO] Trying last-resort content extraction method...{Style.RESET_ALL}")
                    
                    # Get text content from any visible paragraph in the main content area
                    body = driver.find_element(By.TAG_NAME, "body")
                    
                    # Use JavaScript to get all visible text
                    visible_text = driver.execute_script("""
                        function getVisibleText(element) {
                            let text = '';
                            // Skip certain elements that typically don't contain main content
                            if (element.tagName === 'SCRIPT' || element.tagName === 'STYLE' ||
                                element.tagName === 'NOSCRIPT' || element.tagName === 'IFRAME' ||
                                element.tagName === 'HEADER' || element.tagName === 'FOOTER' ||
                                element.tagName === 'NAV') {
                                return '';
                            }
                            
                            // Get computed style to check visibility
                            const style = window.getComputedStyle(element);
                            if (style.display === 'none' || style.visibility === 'hidden' || style.opacity === '0') {
                                return '';
                            }
                            
                            // Get text from this element
                            if (element.tagName === 'P' && element.textContent.trim().length > 0) {
                                text += element.textContent.trim() + '\\n';
                            }
                            
                            // Recursively get text from child elements
                            for (const child of element.children) {
                                text += getVisibleText(child);
                            }
                            
                            return text;
                        }
                        return getVisibleText(arguments[0]);
                    """, body)
                    
                    if visible_text and len(visible_text) > 100:  # Ensure we have meaningful content
                        content = visible_text
                        log_scrape_status(f"{Fore.GREEN}[SUCCESS] Content extracted using JavaScript method: {len(content)} characters{Style.RESET_ALL}")
                except Exception as e:
                    log_scrape_status(f"{Fore.RED}[ERROR] JavaScript content extraction failed: {str(e)}{Style.RESET_ALL}")

            # Verify we have valid content
            if title != "Title Not Found" and content != "Content Not Found":
                # Include title, content, URL, and category in article data
                article_data = {
                    "title": title,
                    "content": content,
                    "url": url,
                    "category": category
                }

                save_article_data(category, article_data, url)  # Pass URL separately
                print(f"{Fore.GREEN}✓ Saved RFA article: {title[:50]}...{Style.RESET_ALL}")
                return article_data
            else:
                # Log detailed debugging information
                log_scrape_status(f"{Fore.RED}[ERROR] Failed to extract complete article from {url}{Style.RESET_ALL}")
                log_scrape_status(f"Title status: {'Found' if title != 'Title Not Found' else 'Not Found'}")
                log_scrape_status(f"Content status: {'Found' if content != 'Content Not Found' else 'Not Found'}")
                
                # Save the page source for debugging
                try:
                    debug_file = f"debug_rfa_failed_{int(time.time())}.html"
                    with open(debug_file, "w", encoding="utf-8") as f:
                        f.write(driver.page_source)
                    log_scrape_status(f"Page source saved to {debug_file} for debugging")
                except Exception as save_err:
                    log_scrape_status(f"Failed to save debug HTML: {str(save_err)}")
                
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
        if driver:  # Check if driver exists before quitting
            try:
                driver.quit()
            except:
                log_scrape_status(f"{Fore.YELLOW}[WARNING] Failed to close driver properly for: {url}")
        log_scrape_status(f"Driver closed for: {url}. Moving to the next URL.")

def scrape_dapnews(url, category):
    return generic_scrape(url, category, "title", "content-main", is_id=True )

@retry_on_exception()  # No parameters here to ensure using global MAX_RETRIES
def scrape_sabay(url, category):
    global success_count, stop_loading
    driver = None
    try:
        chromedriver_path = get_chromedriver_path()
        log_scrape_status(f"Using ChromeDriver from: {chromedriver_path}")
        
        try:
            # Try with Service first
            service = Service(chromedriver_path)
            options = get_chrome_options()
            driver = webdriver.Chrome(service=service, options=options)
        except Exception as driver_init_error:
            log_scrape_status(f"{Fore.YELLOW}[WARNING] Failed to initialize ChromeDriver with explicit path. Trying alternative approach...{Style.RESET_ALL}")
            log_scrape_status(f"Error details: {str(driver_init_error)}")
            
            # Try alternative initialization without Service
            try:
                options = get_chrome_options()
                driver = webdriver.Chrome(options=options)
                log_scrape_status(f"{Fore.GREEN}[SUCCESS] ChromeDriver initialized using alternative method{Style.RESET_ALL}")
            except Exception as alt_error:
                log_scrape_status(f"{Fore.RED}[ERROR] Both initialization methods failed: {str(alt_error)}{Style.RESET_ALL}")
                raise Exception(f"Failed to initialize ChromeDriver: {str(alt_error)}")

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

                save_article_data(category, article_data, url)  # Pass URL separately
                success_count += 1
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
        if driver:  # Check if driver exists before quitting
            try:
                driver.quit()
            except:
                log_scrape_status(f"{Fore.YELLOW}[WARNING] Failed to close driver properly for: {url}")
        log_scrape_status(f"Driver closed for: {url}. Moving to the next URL.")

def scrape_kohsantepheap(url, category):
    return generic_scrape(url, category, "div.article-recap h1", "content-text")

# Map base URLs to their respective scraper functions
SCRAPER_MAP = {
    "https://btv.com.kh": scrape_btv,
    "https://www.postkhmer.com": scrape_postkhmer,
    "https://www.rfa.org": scrape_rfa,
    "https://dap-news.com": scrape_dapnews,
    "https://news.sabay.com.kh": scrape_sabay,
    "https://kohsantepheapdaily.com.kh": scrape_kohsantepheap,
}

# Create directories for category-specific logs
def ensure_log_directories():
    """Ensure log directories exist"""
    os.makedirs(CATEGORY_LOGS_DIR, exist_ok=True)
    os.makedirs(CATEGORY_ERRORS_DIR, exist_ok=True)
    # Also ensure checkpoint directory exists
    os.makedirs(CHECKPOINT_DIR, exist_ok=True)

# No need for URL-to-filename conversion since we're using categories directly
def get_safe_category_name(category):
    """Convert a category to a safe filename"""
    # Remove unsafe filename characters
    return re.sub(r'[\\/*?:"<>|]', "", category)

# Log category-specific errors to JSON
def log_category_error(category, url, error_message, html_file=None):
    """Log error information for a specific category in a JSON file"""
    ensure_log_directories()
    safe_category = get_safe_category_name(category)
    error_file = os.path.join(CATEGORY_ERRORS_DIR, f"{safe_category}_errors.json")
    
    # Initialize or load error data
    error_data = []
    if os.path.exists(error_file):
        try:
            with open(error_file, "r", encoding="utf-8") as f:
                error_data = json.load(f)
        except json.JSONDecodeError:
            log_debug(f"Error reading existing error file for {category}, creating new one")
    
    # Check if this URL already has an error entry
    url_entry = next((item for item in error_data if item["url"] == url), None)
    
    if url_entry:
        # Append new error message if it's not already there
        if error_message not in url_entry["error"]:
            url_entry["error"].append(error_message)
        # Update HTML file reference if provided
        if html_file and html_file != "None":
            url_entry["html_file"] = html_file
    else:
        # Create new entry for this URL
        new_entry = {
            "url": url,
            "error": [error_message],
            "html_file": html_file if html_file else "None"
        }
        error_data.append(new_entry)
    
    # Write updated error data
    with open(error_file, "w", encoding="utf-8") as f:
        json.dump(error_data, f, ensure_ascii=False, indent=4)
    
    log_debug(f"Category error logged to {error_file}")

# Log category-specific progress
def log_category_progress(category, url, message, is_start=False, is_end=False):
    """Log progress for a specific category to a dedicated log file"""
    ensure_log_directories()
    safe_category = get_safe_category_name(category)
    log_file = os.path.join(CATEGORY_LOGS_DIR, f"{safe_category}.log")
    
    timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    divider = "=" * 50
    
    with open(log_file, "a", encoding="utf-8") as f:
        if is_start:
            f.write(f"\n{divider}\n{timestamp} - START PROCESSING URL: {url} (Category: {category})\n{divider}\n")
        
        f.write(f"{timestamp} - {message} (URL: {url})\n")
        
        if is_end:
            f.write(f"{divider}\n{timestamp} - END PROCESSING URL: {url} (Category: {category})\n{divider}\n\n")
    
    # Also log to main log for consistency
    log_debug(message)

# Update the process_url function to use category-specific logging
@retry_on_exception()  # No parameters here to ensure using global MAX_RETRIES  
def process_url(url, category):
    global stop_loading
    stop_loading = False  # Reset animation flag

    log_scrape_status(f"🔄 Starting processing for: {url}")
    log_category_progress(category, url, f"Starting processing for category: {category}", is_start=True)
    
    # Start loading animation in a separate thread
    log_debug(f"Starting loading animation for URL: {url}")
    t = threading.Thread(target=loading_animation, daemon=True)
    t.start()

    try:
        base_url = f"{urlparse(url).scheme}://{urlparse(url).netloc}"
        log_debug(f"Parsed base URL: {base_url}")
        log_scrape_status(f"🔍 Checking scraper function for: {base_url}")
        log_category_progress(category, url, f"Using base URL: {base_url}")
        
        if (base_url in SCRAPER_MAP):
            scraper_function = SCRAPER_MAP[base_url]
            log_scrape_status(f"🔧 Using {scraper_function.__name__} for: {url}")
            log_category_progress(category, url, f"Selected scraper: {scraper_function.__name__}")
            
            log_debug(f"Calling scraper function: {scraper_function.__name__}")
            result = scraper_function(url, category)
            log_debug(f"Scraper function returned. Success: {result is not None}")
            
            if result is not None:
                log_category_progress(category, url, "Scraping completed successfully")
            else:
                log_category_progress(category, url, "Scraper returned None result - possible failure")
                log_category_error(category, url, "Scraper returned None result")
            
            log_scrape_status(f"✅ Finished processing: {url}")
            log_scrape_status(f"➡️ Moving to next URL...")
            
            # Add random delay between requests to avoid overwhelming servers
            delay = 2 + (random.random() * 3)  # Random delay between 2-5 seconds
            log_scrape_status(f"⏱️ Waiting {delay:.1f}s before next request")
            log_category_progress(category, url, f"Waiting {delay:.1f}s before next request")
            time.sleep(delay)
            log_category_progress(category, url, "Processing complete", is_end=True)
            return result
        else:
            error_msg = f"No scraper available for {base_url}"
            log_scrape_status(f"{Fore.RED}[ERROR] {error_msg}{Style.RESET_ALL}")
            log_category_progress(category, url, f"ERROR: {error_msg}")
            log_category_error(category, url, error_msg)
            log_category_progress(category, url, "Processing failed - no scraper available", is_end=True)
            return None
    except Exception as e:
        error_msg = f"Processing URL failed: {str(e)}"
        stack_trace = traceback.format_exc()
        log_scrape_status(f"{Fore.RED}[ERROR] {error_msg}{Style.RESET_ALL}")
        log_debug(f"Exception details for {url}: {str(e)}")
        log_scrape_status(f"Stack trace: {stack_trace}")
        
        # Log detailed error information
        log_category_progress(category, url, f"ERROR: {error_msg}")
        log_category_progress(category, url, f"Stack trace: {stack_trace}")
        log_category_error(category, url, f"{error_msg}; Stack trace available in log")
        log_category_progress(category, url, "Processing failed with exception", is_end=True)
        raise  # Re-raise for retry decorator
    finally:
        log_debug(f"Setting stop_loading flag to True for URL: {url}")
        stop_loading = True  # Stop animation
        time.sleep(0.5)  # Give animation thread time to complete
        log_debug(f"Animation thread should be stopped for URL: {url}")
        log_scrape_status(f"🏁 Completed processing attempt for: {url}")

# Update the generic_scrape function to use category-specific logging
@retry_on_exception()  # No parameters here to ensure using global MAX_RETRIES
def generic_scrape(url, category, title_selector, content_selector, is_id=False):
    global success_count
    
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
        chromedriver_path = get_chromedriver_path()
        
        try:
            # Try with Service first
            service = Service(chromedriver_path)
            options = get_chrome_options()
            log_debug(f"Creating Chrome driver for: {url}")
            driver = webdriver.Chrome(service=service, options=options)
        except Exception as driver_init_error:
            log_scrape_status(f"{Fore.YELLOW}[WARNING] Failed to initialize ChromeDriver with explicit path. Trying alternative approach...{Style.RESET_ALL}")
            log_category_progress(category, url, "Falling back to selenium-manager for ChromeDriver")
            log_scrape_status(f"Error details: {str(driver_init_error)}")
            
            # Try alternative initialization without Service
            try:
                options = get_chrome_options()
                driver = webdriver.Chrome(options=options)
                log_scrape_status(f"{Fore.GREEN}[SUCCESS] ChromeDriver initialized using alternative method{Style.RESET_ALL}")
            except Exception as alt_error:
                log_scrape_status(f"{Fore.RED}[ERROR] Both initialization methods failed: {str(alt_error)}{Style.RESET_ALL}")
                raise Exception(f"Failed to initialize ChromeDriver: {str(alt_error)}")

        try:
            log_scrape_status(f"🔍 Navigating to: {url}")
            driver.get(url)
            log_scrape_status(f"✅ Page loaded for: {url}")
            print(f"Page title: {driver.title}")
            log_scrape_status(f"📄 Page title: {driver.title}")
            log_scrape_status(f"{Fore.CYAN}[DEBUG] Using selectors - Title: {title_selector}, Content: {content_selector}{Style.RESET_ALL}")
            log_category_progress(category, url, f"Navigating to URL")
            log_category_progress(category, url, f"Using selectors - Title: {title_selector}, Content: {content_selector}")
            
            # Track if heartbeat threads are running
            title_heartbeat_running = True
            content_heartbeat_running = True
            
            start_time = time.time()
            
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
                
                # Removed lock wrapping since save_article_data now handles file access safely
                save_article_data(category, article_data, url)  # Pass URL separately
                log_debug("Article data saved, updating checkpoint")
                update_checkpoint(category, url)
                log_debug("Checkpoint updated, incrementing success count")
                success_count += 1
                log_debug(f"Success count incremented to: {success_count}")

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

# Improved save_article_data function with better error handling and timeout
def save_article_data(category, article_data, url=None):
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    output_file = os.path.join(OUTPUT_DIR, f"{category}.json")
    
    log_scrape_status(f"🔄 Starting save process: {article_data['title'][:30]}... to {output_file}")

    try:
        # Load existing data
        existing_data = []
        if os.path.exists(output_file):
            try:
                log_debug(f"Reading existing file: {output_file}")
                with open(output_file, "r", encoding="utf-8") as file:
                    file_content = file.read()
                    if file_content.strip():  # Check if file is not empty
                        existing_data = json.loads(file_content)
                        log_debug(f"Loaded {len(existing_data)} articles from existing file")
                    else:
                        log_debug("File is empty, starting fresh")
            except json.JSONDecodeError:
                log_scrape_status(f"{Fore.YELLOW}⚠️ Warning: JSON file corrupted. Creating backup and resetting.{Style.RESET_ALL}")
                # Create backup of corrupted file
                if os.path.exists(output_file):
                    backup_file = f"{output_file}.bak.{int(time.time())}"
                    try:
                        import shutil
                        shutil.copy2(output_file, backup_file)
                        log_scrape_status(f"Created backup of corrupted file at {backup_file}")
                    except Exception as backup_err:
                        log_scrape_status(f"Failed to backup corrupted file: {backup_err}")
                existing_data = []
            except Exception as read_err:
                log_scrape_status(f"{Fore.RED}❌ [ERROR] Failed to read existing file: {read_err}{Style.RESET_ALL}")
                existing_data = []

        # Append new article
        existing_data.append(article_data)

        # Write data to file using a temporary file for safety
        temp_file = f"{output_file}.temp"
        try:
            log_debug(f"Writing to temporary file: {temp_file}")
            with open(temp_file, "w", encoding="utf-8") as file:
                json.dump(existing_data, file, ensure_ascii=False, indent=4)
            log_debug(f"Temporary file written successfully")
            
            # Replace original file with updated file
            if os.path.exists(output_file):
                os.replace(temp_file, output_file)
            else:
                os.rename(temp_file, output_file)
            
            log_debug(f"File saved successfully to {output_file}")
            log_scrape_status(f"{Fore.GREEN}✅ Successfully saved article: {article_data['title'][:50]}... Moving to next URL.{Style.RESET_ALL}")
            
            # Update checkpoint
            if url:
                log_debug(f"Updating checkpoint for URL: {url}")
                update_checkpoint(category, url)
        except Exception as write_err:
            log_scrape_status(f"{Fore.RED}❌ [ERROR] Failed to write file {output_file}: {write_err}{Style.RESET_ALL}")
            if os.path.exists(temp_file):
                try:
                    os.remove(temp_file)
                    log_debug(f"Removed temporary file after error: {temp_file}")
                except:
                    pass

    except Exception as e:
        log_scrape_status(f"{Fore.RED}❌ [ERROR] General error in save_article_data: {e}{Style.RESET_ALL}")
        log_scrape_status(f"Stack trace: {traceback.format_exc()}")

def get_checkpoint(category):
    if os.path.exists(CHECKPOINT_FILE):
        with open(CHECKPOINT_FILE, "r", encoding="utf-8") as file:
            checkpoint_data = json.load(file)
        return checkpoint_data.get(category, None)
    return None

# Add a file-specific lock for each file being processed
file_locks = {}

# Modified to handle concurrent file processing while maintaining sequential URL processing within each file
def process_file(file):
    category = os.path.splitext(os.path.basename(file))[0]
    
    # Create a thread identifier for logging
    thread_id = threading.current_thread().name
    
    log_scrape_status(f"[Thread {thread_id}] Starting to process category: {category}")
    
    try:
        with open(file, "r", encoding="utf-8") as f:
            urls = json.load(f)
        
        log_scrape_status(f"[Thread {thread_id}] Total URLs to process: {len(urls)} for category {category}")
    
        processed = 0
        failed = 0
        for i, url in enumerate(urls):
            try:
                log_scrape_status(f"[Thread {thread_id}] ⏳ Processing URL {i+1}/{len(urls)}: {url}")
                log_category_progress(category, url, f"Starting processing as URL {i+1}/{len(urls)} in category {category}", is_start=True)
                
                result = process_url(url, category)
                
                if result is not None:
                    processed += 1
                    log_scrape_status(f"[Thread {thread_id}] ✅ Successfully scraped URL {i+1}: {url}")
                    log_category_progress(category, url, "Successfully scraped and saved article")
                else:
                    failed += 1
                    log_scrape_status(f"[Thread {thread_id}] ⚠️ URL returned None result: {url}")
                    log_category_progress(category, url, "WARNING: URL returned None result")
                    log_category_error(category, url, "URL returned None result")
                
                log_category_progress(category, url, "Processing complete", is_end=True)
            except Exception as e:
                failed += 1
                error_msg = f"Failed to process URL: {str(e)}"
                log_scrape_status(f"[Thread {thread_id}] {Fore.RED}❌ [ERROR] {error_msg}{Style.RESET_ALL}")
                log_category_progress(category, url, f"ERROR: {error_msg}", is_end=True)
                log_category_error(category, url, error_msg)
                # Continue with the next URL instead of stopping
                continue
                
            log_scrape_status(f"[Thread {thread_id}] 📊 Progress: {processed} successful, {failed} failed, {i+1}/{len(urls)} total")
            log_scrape_status(f"[Thread {thread_id}] ➡️ Moving to next URL in category {category}...")
        
        log_scrape_status(f"[Thread {thread_id}] {Fore.GREEN}[COMPLETE] Category {category}: {processed}/{len(urls)} articles processed, {failed} failed{Style.RESET_ALL}")
        return {"category": category, "processed": processed, "failed": failed, "total": len(urls)}
    except Exception as e:
        log_scrape_status(f"[Thread {thread_id}] {Fore.RED}❌ [ERROR] Failed to process category {category}: {str(e)}{Style.RESET_ALL}")
        log_scrape_status(f"[Thread {thread_id}] Stack trace: {traceback.format_exc()}")
        return {"category": category, "processed": 0, "failed": 0, "total": 0, "error": str(e)}

if __name__ == "__main__":
    import random  # For random delays
    import psutil  # For memory tracking
    import concurrent.futures
    import argparse
    import subprocess
    
    def log_memory_usage():
        process = psutil.Process(os.getpid())
        memory = process.memory_info().rss / 1024 / 1024  # Convert to MB
        log_scrape_status(f"{Fore.CYAN}Memory usage: {memory:.2f} MB{Style.RESET_ALL}")
    
    # Parse command line arguments
    parser = argparse.ArgumentParser(description='Article Crawler for Khmer News')
    parser.add_argument('--reset-checkpoint', action='store_true', help='Reset the checkpoint file')
    parser.add_argument('--category', help='Specific category to process')
    args = parser.parse_args()
    
    # Reset checkpoint if requested
    if args.reset_checkpoint:
        if os.path.exists(CHECKPOINT_FILE):
            os.remove(CHECKPOINT_FILE)
            log_scrape_status(f"{Fore.YELLOW}Checkpoint file reset.{Style.RESET_ALL}")
    
    # Create necessary directories
    os.makedirs(INPUT_DIR, exist_ok=True)
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    os.makedirs(CHECKPOINT_DIR, exist_ok=True)
    os.makedirs(LOGS_DIR, exist_ok=True)
    
    # Create log directories at startup
    ensure_log_directories()
    
    log_scrape_status(f"{Fore.GREEN}========================{Style.RESET_ALL}")
    log_scrape_status(f"{Fore.GREEN}STARTING ARTICLE CRAWLER{Style.RESET_ALL}")
    log_scrape_status(f"{Fore.GREEN}========================{Style.RESET_ALL}")
    log_scrape_status(f"{Fore.CYAN}[INFO] Starting with MAX_WAIT_TIME={MAX_WAIT_TIME}s, MAX_RETRIES={MAX_RETRIES}{Style.RESET_ALL}")
    log_scrape_status(f"{Fore.CYAN}[INFO] Input directory: {INPUT_DIR}{Style.RESET_ALL}")
    log_scrape_status(f"{Fore.CYAN}[INFO] Output directory: {OUTPUT_DIR}{Style.RESET_ALL}")
    log_scrape_status(f"{Fore.CYAN}[INFO] Checkpoint file: {CHECKPOINT_FILE}{Style.RESET_ALL}")
    log_scrape_status(f"{Fore.CYAN}[INFO] Log directories: {CATEGORY_LOGS_DIR} and {CATEGORY_ERRORS_DIR}{Style.RESET_ALL}")
    
    # Check for ChromeDriver and suggest installation if needed
    def check_chromedriver():
        chromedriver_path = get_chromedriver_path()
        if chromedriver_path == "chromedriver":
            # If we're just using the command name, verify if it works
            try:
                subprocess.run(["chromedriver", "--version"], 
                              stdout=subprocess.PIPE, 
                              stderr=subprocess.PIPE, 
                              check=True, 
                              text=True)
                log_scrape_status(f"{Fore.GREEN}[INFO] ChromeDriver is available in PATH{Style.RESET_ALL}")
            except (subprocess.SubprocessError, FileNotFoundError):
                log_scrape_status(f"{Fore.RED}[ERROR] ChromeDriver not found. Please install ChromeDriver and ensure it's in PATH.{Style.RESET_ALL}")
                log_scrape_status(f"{Fore.YELLOW}[INFO] Download ChromeDriver from: https://chromedriver.chromium.org/downloads{Style.RESET_ALL}")
                if sys.platform.startswith('darwin'):  # macOS
                    log_scrape_status(f"{Fore.YELLOW}[INFO] Install with: brew install chromedriver{Style.RESET_ALL}")
                elif sys.platform.startswith('linux'):  # Linux
                    log_scrape_status(f"{Fore.YELLOW}[INFO] Install with: apt install chromium-chromedriver{Style.RESET_ALL}")
    
    # Run the ChromeDriver check
    check_chromedriver()
    
    # Get list of JSON files to process
    if args.category:
        # If specific category is provided, only process that one
        target_file = os.path.join(INPUT_DIR, f"{args.category}.json")
        if os.path.exists(target_file):
            files = [target_file]
            log_scrape_status(f"Processing single category: {args.category}")
        else:
            log_scrape_status(f"{Fore.RED}[ERROR] Category file not found: {args.category}.json{Style.RESET_ALL}")
            sys.exit(1)
    else:
        # Process all categories
        files = [os.path.join(INPUT_DIR, file) for file in os.listdir(INPUT_DIR) if file.endswith(".json")]
        log_scrape_status(f"Found {len(files)} URL files to process")
    
    if len(files) == 0:
        log_scrape_status(f"{Fore.YELLOW}[WARNING] No JSON files found in {INPUT_DIR}. Please add URL files before running.{Style.RESET_ALL}")
        sys.exit(1)
    
    # Track results across all files
    total_processed = 0
    total_failed = 0
    total_urls = 0
    total_files_processed = 0

    # Process files concurrently with ThreadPoolExecutor (up to 6 files at a time)
    log_scrape_status(f"{Fore.CYAN}Starting concurrent processing of up to {min(6, len(files))} files at a time{Style.RESET_ALL}")
    with concurrent.futures.ThreadPoolExecutor(max_workers=6) as executor:
        # Submit all files for processing
        future_to_file = {executor.submit(process_file, file): file for file in files}
        
        # Process results as they complete
        for future in concurrent.futures.as_completed(future_to_file):
            file = future_to_file[future]
            category = os.path.splitext(os.path.basename(file))[0]
            try:
                result = future.result()
                if "error" in result:
                    log_scrape_status(f"{Fore.RED}❌ [ERROR] Failed to process file {file}: {result['error']}{Style.RESET_ALL}")
                else:
                    total_processed += result["processed"]
                    total_failed += result["failed"]
                    total_urls += result["total"]
                    total_files_processed += 1
                    
                    # Log completion of this file
                    log_scrape_status(f"{Fore.GREEN}✅ Finished processing file: {file}, {result['processed']}/{result['total']} articles processed, {result['failed']} failed{Style.RESET_ALL}")
            except Exception as exc:
                log_scrape_status(f"{Fore.RED}❌ [ERROR] File {file} generated an exception: {exc}{Style.RESET_ALL}")
            finally:
                # Force garbage collection after each file completes
                import gc
                gc.collect()
                log_debug(f"Garbage collection performed after file: {file}")
                log_memory_usage()  # Track memory after garbage collection

    # Final message after scraping
    log_scrape_status(f"\n{Fore.GREEN}✅ Scraping completed! Successfully saved {total_processed} articles from {total_files_processed}/{len(files)} files.{Style.RESET_ALL}")
    log_scrape_status(f"{Fore.GREEN}Total URLs: {total_urls}, Successful: {total_processed}, Failed: {total_failed}{Style.RESET_ALL}")
    log_scrape_status(f"{Fore.GREEN}========================{Style.RESET_ALL}")


