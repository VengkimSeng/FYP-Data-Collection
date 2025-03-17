"""
Shutdown mechanism for the article crawler.
"""

import os
import sys
import signal
import atexit
from colorama import Fore, Style

from src.extractors.logger import log_scrape_status

# Flag to track if shutdown is in progress
shutdown_in_progress = False

def shutdown_handler(sig=None, frame=None):
    """Handle shutdown signal by closing resources and exiting cleanly."""
    global shutdown_in_progress
    
    # Prevent multiple shutdown attempts
    if shutdown_in_progress:
        return
        
    shutdown_in_progress = True
    
    log_scrape_status(f"{Fore.YELLOW}Shutdown signal received. Performing clean shutdown...{Style.RESET_ALL}")
    
    # Clean up resources 
    try:
        log_scrape_status("Saving any unsaved data...")
        # Any final save operations would go here
        
        log_scrape_status("Closing browser instances...")
        # Close any leftover browser instances by force if needed
        try:
            import psutil
            current_process = psutil.Process(os.getpid())
            children = current_process.children(recursive=True)
            
            for child in children:
                if "chrome" in child.name().lower() or "chromium" in child.name().lower():
                    log_scrape_status(f"Terminating browser process: {child.pid}")
                    child.terminate()
        except ImportError:
            log_scrape_status("psutil not available, skipping browser cleanup")
        except Exception as e:
            log_scrape_status(f"Error during browser cleanup: {e}")
            
        log_scrape_status(f"{Fore.GREEN}Shutdown complete. Exiting.{Style.RESET_ALL}")
    except Exception as e:
        log_scrape_status(f"{Fore.RED}Error during shutdown: {e}{Style.RESET_ALL}")
        
    # Exit the program
    sys.exit(0)

def setup_shutdown_handlers():
    """Set up signal handlers for graceful shutdown."""
    # Register shutdown function to run at exit
    atexit.register(shutdown_handler)
    
    # Register signal handlers for common termination signals
    signal.signal(signal.SIGINT, shutdown_handler)   # Ctrl+C
    signal.signal(signal.SIGTERM, shutdown_handler)  # kill command
    
    # Create a shutdown file that can be used to trigger shutdown
    create_shutdown_file()
    
    log_scrape_status(f"{Fore.CYAN}Shutdown handlers initialized. To stop the crawler:\n"
                     f"1. Press Ctrl+C in this terminal\n"
                     f"2. Run 'kill {os.getpid()}' from another terminal\n"
                     f"3. Create a file named 'shutdown.signal' in the current directory{Style.RESET_ALL}")

def create_shutdown_file():
    """Create a shutdown file that can be monitored to trigger shutdown."""
    # Remove any existing shutdown file
    if os.path.exists("shutdown.signal"):
        try:
            os.remove("shutdown.signal")
            log_scrape_status("Removed existing shutdown.signal file")
        except Exception as e:
            log_scrape_status(f"Warning: Could not remove existing shutdown.signal file: {e}")

def check_for_shutdown():
    """Check if shutdown has been requested via file."""
    if os.path.exists("shutdown.signal"):
        log_scrape_status(f"{Fore.YELLOW}Shutdown file detected. Initiating shutdown...{Style.RESET_ALL}")
        shutdown_handler()
        return True
    return False
