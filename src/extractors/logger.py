"""
Logging utilities for the article extractor.
"""

import os
import sys
import logging
from datetime import datetime
from colorama import Fore, Style, init

# Initialize colorama
init(autoreset=True)

# Log files
LOG_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), "logs", "extractors")

# Create logger
logger = logging.getLogger("article_extractor")
logger.setLevel(logging.DEBUG)

# Create console handler
console_handler = logging.StreamHandler()
console_handler.setLevel(logging.INFO)

def ensure_log_directories():
    """Ensure log directories exist."""
    os.makedirs(LOG_DIR, exist_ok=True)
    
    # Create category-specific directory
    category_log_dir = os.path.join(LOG_DIR, "categories")
    os.makedirs(category_log_dir, exist_ok=True)
    
    # Create error log directory
    error_log_dir = os.path.join(LOG_DIR, "errors")
    os.makedirs(error_log_dir, exist_ok=True)
    
    # Create debug log directory
    debug_log_dir = os.path.join(LOG_DIR, "debug")
    os.makedirs(debug_log_dir, exist_ok=True)

# Create file handlers
def setup_file_handlers():
    """Set up file handlers for logging."""
    # Main log file
    main_log_file = os.path.join(LOG_DIR, f"extractor_{datetime.now().strftime('%Y%m%d')}.log")
    main_file_handler = logging.FileHandler(main_log_file)
    main_file_handler.setLevel(logging.INFO)
    
    # Error log file
    error_log_file = os.path.join(LOG_DIR, "errors", f"errors_{datetime.now().strftime('%Y%m%d')}.log")
    error_file_handler = logging.FileHandler(error_log_file)
    error_file_handler.setLevel(logging.ERROR)
    
    # Debug log file
    debug_log_file = os.path.join(LOG_DIR, "debug", f"debug_{datetime.now().strftime('%Y%m%d')}.log")
    debug_file_handler = logging.FileHandler(debug_log_file)
    debug_file_handler.setLevel(logging.DEBUG)
    
    # Create formatters
    formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    main_file_handler.setFormatter(formatter)
    error_file_handler.setFormatter(formatter)
    debug_file_handler.setFormatter(formatter)
    console_handler.setFormatter(formatter)
    
    # Add handlers to logger
    logger.addHandler(main_file_handler)
    logger.addHandler(error_file_handler)
    logger.addHandler(debug_file_handler)
    logger.addHandler(console_handler)

# Ensure directories exist
ensure_log_directories()

# Set up file handlers
setup_file_handlers()

def log_scrape_status(message: str):
    """Log a message to console and file."""
    # Print to console with color
    print(message)
    
    # Strip color codes for log file
    clean_message = message
    for color in [Fore.RED, Fore.GREEN, Fore.YELLOW, Fore.BLUE, Fore.MAGENTA, Fore.CYAN, Fore.WHITE, Style.RESET_ALL]:
        clean_message = clean_message.replace(color, '')
    
    # Log to file
    logger.info(clean_message)

def log_error(message: str, exc=None):
    """Log an error message and exception."""
    log_scrape_status(f"{Fore.RED}{message}{Style.RESET_ALL}")
    if exc:
        logger.error(f"{message}: {exc}", exc_info=True)
    else:
        logger.error(message)

def log_debug(message: str):
    """Log a debug message."""
    logger.debug(message)

def log_category_progress(category: str, current: int, total: int, success: int, errors: int, is_end: bool = False):
    """
    Log category processing progress.
    
    Args:
        category: Category being processed
        current: Current item number
        total: Total items to process
        success: Number of successfully processed items
        errors: Number of errors
        is_end: Whether this is the final progress update
    """
    percent = (current / total) * 100 if total > 0 else 0
    status = "COMPLETE" if is_end else "Progress"
    message = f"[{category}] {status}: {current}/{total} ({percent:.1f}%) - Success: {success}, Errors: {errors}"
    log_scrape_status(f"{Fore.CYAN}{message}{Style.RESET_ALL}")

def log_category_error(category: str, error_msg: str):
    """
    Log an error related to a specific category.
    
    Args:
        category: Category name
        error_msg: Error message
    """
    message = f"[{category}] ERROR: {error_msg}"
    log_error(message)
