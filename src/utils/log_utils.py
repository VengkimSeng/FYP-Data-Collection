import os
import sys
import logging
import datetime
from pathlib import Path
from colorama import Fore, Back, Style, init
from typing import Dict

# Initialize colorama
init(autoreset=True)

# Color mapping for different crawlers
CRAWLER_COLORS: Dict[str, str] = {
    'sabaynews': Fore.CYAN,
    'postkhmer': Fore.GREEN,
    'btv': Fore.YELLOW,
    'dapnews': Fore.MAGENTA, 
    'rfa': Fore.BLUE,
    'kohsantepheap': Fore.RED
}

# Log levels colors
LEVEL_COLORS = {
    'DEBUG': Fore.BLUE,
    'INFO': Fore.GREEN,
    'WARNING': Fore.YELLOW,
    'ERROR': Fore.RED,
    'CRITICAL': Fore.RED + Back.WHITE
}

class ColoredFormatter(logging.Formatter):
    def format(self, record):
        # Get the crawler name from the module path
        module_path = record.pathname
        crawler_name = Path(module_path).stem.replace('_crawler', '')
        
        # Add crawler color
        crawler_color = CRAWLER_COLORS.get(crawler_name, '')
        
        # Add level color
        level_color = LEVEL_COLORS.get(record.levelname, '')
        
        # Format the message with colors and source info
        record.msg = f"{crawler_color}[{crawler_name}] {level_color}{record.msg}{Style.RESET_ALL}"
        
        # Add source file info
        relative_path = os.path.relpath(record.pathname)
        record.msg = f"{record.msg} {Fore.WHITE}({relative_path}:{record.lineno}){Style.RESET_ALL}"
        
        return super().format(record)

def setup_logger(name: str, log_file: str = None, level=logging.INFO):
    """Configure and return a logger with colored output"""
    logger = logging.getLogger(name)
    logger.setLevel(level)
    
    # Create formatters
    console_formatter = ColoredFormatter(
        '%(asctime)s | %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    
    file_formatter = logging.Formatter(
        '%(asctime)s | %(name)s | %(levelname)s | %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    
    # Console handler
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setFormatter(console_formatter)
    logger.addHandler(console_handler)
    
    # File handler (if log_file specified)
    if log_file:
        os.makedirs(os.path.dirname(log_file), exist_ok=True)
        file_handler = logging.FileHandler(log_file)
        file_handler.setFormatter(file_formatter)
        logger.addHandler(file_handler)
    
    return logger

def get_crawler_logger(crawler_name: str):
    """Get a logger specifically for a crawler with appropriate color coding"""
    log_dir = "output/logs/crawlers"
    os.makedirs(log_dir, exist_ok=True)
    log_file = os.path.join(log_dir, f"{crawler_name}.log")
    return setup_logger(f"crawler.{crawler_name}", log_file)
