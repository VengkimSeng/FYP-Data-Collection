import os
import sys
import logging
import datetime
from pathlib import Path
from colorama import Fore, Back, Style, init
from typing import Dict, Optional
import threading

# Initialize colorama
init(autoreset=True)

# Global log lock to prevent race conditions when writing to log files
LOG_LOCK = threading.RLock()

# Color mapping for different crawlers
CRAWLER_COLORS: Dict[str, str] = {
    'sabaynews': Fore.CYAN,
    'postkhmer': Fore.GREEN,
    'btv': Fore.YELLOW,
    'dapnews': Fore.MAGENTA, 
    'rfa': Fore.BLUE,
    'kohsantepheap': Fore.RED,
    'master_controller': Fore.WHITE + Style.BRIGHT
}

# Colors for the 6 main categories
CATEGORY_COLORS: Dict[str, str] = {
    'politic': Fore.RED,
    'economic': Fore.GREEN,
    'technology': Fore.BLUE,
    'sport': Fore.YELLOW,
    'health': Fore.MAGENTA,
    'environment': Fore.CYAN
}

# Log levels colors
LEVEL_COLORS = {
    'DEBUG': Fore.BLUE,
    'INFO': Fore.GREEN,
    'WARNING': Fore.YELLOW,
    'ERROR': Fore.RED,
    'CRITICAL': Fore.RED + Back.WHITE
}

# Define base log directory
BASE_LOG_DIR = os.path.join(os.getcwd(), "output", "logs")

class ColoredFormatter(logging.Formatter):
    """Custom formatter that adds color and source information to log messages."""
    
    def format(self, record):
        # Get the crawler name from the logger name or module path
        if hasattr(record, 'crawler_name'):
            crawler_name = record.crawler_name
        else:
            module_path = record.pathname
            crawler_name = Path(module_path).stem.replace('_crawler', '')
        
        # Add crawler color based on name
        crawler_color = CRAWLER_COLORS.get(crawler_name, '')
        
        # Add category color if applicable
        category_name = getattr(record, 'category', None)
        category_color = CATEGORY_COLORS.get(category_name, '') if category_name else ''
        
        # Add level color
        level_color = LEVEL_COLORS.get(record.levelname, '')
        
        # Format differently based on output destination (file vs console)
        if any(isinstance(h, logging.StreamHandler) and h.stream == sys.stdout 
               for h in logging.getLogger(record.name).handlers):
            # For console output, use colors
            record.msg = f"{crawler_color}[{crawler_name}] {level_color}{record.msg}{Style.RESET_ALL}"
            
            # Add category info if available
            if category_name:
                record.msg = f"{category_color}[{category_name}] {record.msg}"
        else:
            # For file output, don't use colors but include all information
            record.msg = f"[{crawler_name}] {record.msg}"
            
            # Add category info if available
            if category_name:
                record.msg = f"[{category_name}] {record.msg}"
        
        return super().format(record)

class SafeFileHandler(logging.FileHandler):
    """Thread-safe file handler that uses a lock when writing."""
    
    def __init__(self, filename, mode='a', encoding=None, delay=False):
        super().__init__(filename, mode, encoding, delay)
        
    def emit(self, record):
        with LOG_LOCK:
            super().emit(record)
            # Force flush to ensure logs are written immediately - important for server environments
            self.flush()

def setup_logger(name: str, log_file: Optional[str] = None, level=logging.INFO, 
                 formatter=None, console=True):
    """
    Set up a logger with file and optional console handlers
    
    Args:
        name: Logger name
        log_file: Path to log file (optional)
        level: Logging level
        formatter: Optional formatter to use
        console: Whether to add console handler
        
    Returns:
        Logger object
    """
    # Create logger
    logger = logging.getLogger(name)
    logger.setLevel(level)
    logger.propagate = False  # Don't pass messages to ancestor loggers
    
    # Remove existing handlers to prevent duplicates
    for handler in logger.handlers[:]:
        logger.removeHandler(handler)
    
    # Create formatters
    if formatter is None:
        # Different formatters for console vs file
        console_formatter = ColoredFormatter(
            '%(asctime)s | %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S'
        )
        
        file_formatter = logging.Formatter(
            '%(asctime)s | %(name)s | %(levelname)s | %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S'
        )
    else:
        console_formatter = formatter
        file_formatter = formatter
    
    # Add console handler if requested
    if console:
        console_handler = logging.StreamHandler(stream=sys.stdout)
        console_handler.setFormatter(console_formatter)
        logger.addHandler(console_handler)
    
    # Add file handler if log_file provided
    if log_file:
        # Ensure directory exists
        os.makedirs(os.path.dirname(os.path.abspath(log_file)), exist_ok=True)
        file_handler = SafeFileHandler(log_file, mode='a', encoding='utf-8')
        file_handler.setFormatter(file_formatter)
        logger.addHandler(file_handler)
        
        # Also add a handler for errors that writes to an error-specific log
        error_log = log_file.replace('.log', '_errors.log')
        error_handler = SafeFileHandler(error_log, mode='a', encoding='utf-8')
        error_handler.setFormatter(file_formatter)
        error_handler.setLevel(logging.ERROR)  # Only log errors and above
        logger.addHandler(error_handler)
    
    return logger

def get_crawler_logger(crawler_name: str):
    """
    Get a logger specifically for a crawler with appropriate color coding.
    
    Args:
        crawler_name: Name of the crawler (e.g., 'btv', 'postkhmer')
        
    Returns:
        Logger instance
    """
    # Create logs directory in output folder
    log_dir = os.path.join(BASE_LOG_DIR, "crawlers")
    os.makedirs(log_dir, exist_ok=True)
    log_file = os.path.join(log_dir, f"{crawler_name}.log")
    
    # Create the logger
    logger = setup_logger(f"crawler.{crawler_name}", log_file)
    
    # Add a filter to attach crawler name to all log records
    class CrawlerFilter(logging.Filter):
        def filter(self, record):
            record.crawler_name = crawler_name
            return True
    
    # Apply the filter to all handlers
    for handler in logger.handlers:
        handler.addFilter(CrawlerFilter())
    
    return logger

def get_category_logger(category_name: str):
    """
    Get a logger specifically for a category with appropriate color coding.
    
    Args:
        category_name: Name of the category (e.g., 'politic', 'sport')
        
    Returns:
        Logger instance
    """
    # Create category logs directory in output folder
    log_dir = os.path.join(BASE_LOG_DIR, "categories")
    os.makedirs(log_dir, exist_ok=True)
    log_file = os.path.join(log_dir, f"{category_name}.log")
    
    # Create the logger
    logger = setup_logger(f"category.{category_name}", log_file)
    
    # Add a filter to attach category name to all log records
    class CategoryFilter(logging.Filter):
        def filter(self, record):
            record.category = category_name
            return True
    
    # Apply the filter to all handlers
    for handler in logger.handlers:
        handler.addFilter(CategoryFilter())
    
    return logger

def get_master_logger():
    """
    Get a logger specifically for the master crawler controller.
    
    Returns:
        Logger instance
    """
    # Create main log directory in output folder
    log_dir = BASE_LOG_DIR
    os.makedirs(log_dir, exist_ok=True)
    log_file = os.path.join(log_dir, "master_crawler_controller.log")
    
    # Create the logger with a specific name
    logger = setup_logger("master_controller", log_file)
    
    # Add a filter to set crawler_name
    class MasterFilter(logging.Filter):
        def filter(self, record):
            record.crawler_name = "master_controller"
            return True
    
    # Apply the filter to all handlers
    for handler in logger.handlers:
        handler.addFilter(MasterFilter())
    
    return logger

def log_with_context(logger, level, message, crawler=None, category=None, **kwargs):
    """
    Log a message with crawler and category context.
    
    Args:
        logger: Logger to use
        level: Log level (e.g., 'INFO', 'ERROR')
        message: Log message
        crawler: Crawler name (optional)
        category: Category name (optional)
        **kwargs: Additional log record attributes
    """
    extra = {}
    if crawler:
        extra['crawler_name'] = crawler
    if category:
        extra['category'] = category
    
    # Add any additional context
    for key, value in kwargs.items():
        extra[key] = value
    
    # Log with the specified level
    if level == 'DEBUG':
        logger.debug(message, extra=extra)
    elif level == 'INFO':
        logger.info(message, extra=extra)
    elif level == 'WARNING':
        logger.warning(message, extra=extra)
    elif level == 'ERROR':
        logger.error(message, extra=extra)
    elif level == 'CRITICAL':
        logger.critical(message, extra=extra)
    else:
        logger.info(message, extra=extra)
