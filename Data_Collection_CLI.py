#!/usr/bin/env python3
"""
Data Collection CLI

A terminal-based interface for controlling the FYP data collection process.
Features:
- Run individual components (crawl only, extract only)
- Configure settings (URL count, extract workers)
- Control specific categories
- Test crawlers
- Sync folders
"""

import os
import sys
import json
import signal
import subprocess
import time
import argparse
import threading
import traceback
from datetime import datetime
from colorama import Fore, Style, init

#################################################################################
#                               INITIALIZATION                                   #
#################################################################################
"""
This section handles the initial setup of the application, including:
- Colorama initialization for colored terminal output
- Global configuration variables
- Signal handlers for graceful shutdown
"""

# Initialize colorama
init(autoreset=True)

# Global variables for configuration
CONFIG = {
    "urls_per_category": 2500,
    "crawl_workers": 4,
    "extract_workers": 6,
    "output_dir": "output/articles",
    "urls_dir": "output/urls",
    "categories_file": "config/categories.json",
    "running_process": None,  # Store the running subprocess
    "stop_requested": False    # Flag to track stop requests
}

# Set up signal handler for graceful exit
def signal_handler(sig, frame):
    """Handle interrupt signals (Ctrl+C)
    
    When the user presses Ctrl+C, this handler ensures:
    1. The stop_requested flag is set
    2. Any running subprocess is terminated gracefully
    3. If graceful termination fails, the process is forcibly killed
    4. User is informed they can resume later
    
    Args:
        sig: Signal number
        frame: Current stack frame
    """
    print(f"\n{Fore.YELLOW}Stop requested. Gracefully shutting down...{Style.RESET_ALL}")
    CONFIG["stop_requested"] = True
    
    # If there's a running process, terminate it gracefully
    if CONFIG["running_process"] and CONFIG["running_process"].poll() is None:
        print(f"{Fore.YELLOW}Terminating running process...{Style.RESET_ALL}")
        CONFIG["running_process"].terminate()
        try:
            CONFIG["running_process"].wait(timeout=5)
            print(f"{Fore.GREEN}Process terminated successfully.{Style.RESET_ALL}")
        except subprocess.TimeoutExpired:
            print(f"{Fore.RED}Process did not terminate gracefully, forcing...{Style.RESET_ALL}")
            CONFIG["running_process"].kill()
    
    print(f"{Fore.GREEN}Shutdown complete. You can resume later using the appropriate menu option.{Style.RESET_ALL}")
    sys.exit(0)

# Register the signal handler
signal.signal(signal.SIGINT, signal_handler)
signal.signal(signal.SIGTERM, signal_handler)

#################################################################################
#                              USER INTERFACE                                    #
#################################################################################
"""
This section contains functions that handle the user interface elements:
- Terminal screen clearing
- Header and status display
- Menu rendering
"""

def clear_screen():
    """Clear the terminal screen
    
    Uses the appropriate command based on the operating system:
    - 'cls' for Windows
    - 'clear' for Unix-based systems (macOS, Linux)
    """
    os.system('cls' if os.name == 'nt' else 'clear')

def print_header():
    """Print the application header
    
    Displays a formatted header with the application name,
    clearing the screen first for a clean interface.
    """
    clear_screen()
    print(f"{Fore.CYAN}{'=' * 80}{Style.RESET_ALL}")
    print(f"{Fore.CYAN}{' ' * 25}KHMER NEWS DATA COLLECTION TOOL{' ' * 25}{Style.RESET_ALL}")
    print(f"{Fore.CYAN}{'=' * 80}{Style.RESET_ALL}")
    print()

def print_status():
    """Print the current configuration status
    
    Displays all current configuration settings to keep the user informed
    about the parameters that will be used for operations.
    """
    print(f"\n{Fore.YELLOW}Current Settings:{Style.RESET_ALL}")
    print(f"  URLs per category: {CONFIG['urls_per_category']}")
    print(f"  Extract workers: {CONFIG['extract_workers']}")
    print(f"  Output directory: {CONFIG['output_dir']}")
    print(f"  URLs directory: {CONFIG['urls_dir']}")
    print(f"  Categories file: {CONFIG['categories_file']}")
    print()

#################################################################################
#                              PROCESS EXECUTION                                 #
#################################################################################
"""
This section handles the execution of external processes:
- Running subprocesses for crawling and extraction
- Displaying real-time output
- Handling process termination
"""

def run_command(command, description):
    """Run a subprocess command with progress indication
    
    Executes an external command as a subprocess, captures its output in real-time,
    and displays it to the user. Stores the process reference to allow for
    graceful termination if needed.
    
    Args:
        command: List of command parts to execute
        description: Human-readable description of the command
        
    Returns:
        bool: True if the process completed successfully (return code 0), False otherwise
    """
    print(f"{Fore.GREEN}Starting: {description}{Style.RESET_ALL}")
    print(f"{Fore.CYAN}Running command: {' '.join(command)}{Style.RESET_ALL}")
    print(f"{Fore.YELLOW}Press Ctrl+C to stop at any time{Style.RESET_ALL}")
    
    # Start the process and store it in CONFIG
    CONFIG["running_process"] = subprocess.Popen(
        command, 
        stdout=subprocess.PIPE, 
        stderr=subprocess.STDOUT,
        bufsize=1,  # Line buffered
        universal_newlines=True,
        encoding='utf-8',
        errors='replace'
    )
    
    # Track real-time output
    for line in CONFIG["running_process"].stdout:
        print(line, end='')
    
    return_code = CONFIG["running_process"].wait()
    CONFIG["running_process"] = None
    
    if return_code == 0:
        print(f"{Fore.GREEN}✅ {description} completed successfully.{Style.RESET_ALL}")
        return True
    else:
        print(f"{Fore.RED}❌ {description} failed with return code {return_code}.{Style.RESET_ALL}")
        return False

#################################################################################
#                              CATEGORY HANDLING                                 #
#################################################################################
"""
This section manages category-related operations:
- Loading categories from configuration files
- Allowing user selection of categories
- Category filtering and validation
"""

def load_categories():
    """Load available categories from the configuration file
    
    Reads the categories JSON file and loads its contents.
    
    Returns:
        list: List of category names, or empty list if loading failed
    """
    try:
        with open(CONFIG["categories_file"], 'r', encoding='utf-8') as f:
            categories_data = json.load(f)
            return list(categories_data.keys())
    except Exception as e:
        print(f"{Fore.RED}Error loading categories: {str(e)}{Style.RESET_ALL}")
        return []

def select_categories():
    """Allow user to select specific categories or all
    
    Displays a numbered list of available categories and lets the user
    choose one specific category or all categories.
    
    Returns:
        list: Selected category names, all categories, or None if operation cancelled
    """
    categories = load_categories()
    if not categories:
        print(f"{Fore.RED}Failed to load categories. Please check the categories file.{Style.RESET_ALL}")
        return None
    
    print(f"{Fore.GREEN}Available categories:{Style.RESET_ALL}")
    for idx, category in enumerate(categories, 1):
        print(f"  {idx}. {category}")
    print(f"  {len(categories) + 1}. All categories")
    print(f"  0. Cancel")
    
    try:
        choice = int(input(f"\n{Fore.YELLOW}Select an option (0-{len(categories) + 1}): {Style.RESET_ALL}"))
        if choice == 0:
            return None
        elif choice == len(categories) + 1:
            return categories  # All categories
        elif 1 <= choice <= len(categories):
            return [categories[choice - 1]]  # Single category
        else:
            print(f"{Fore.RED}Invalid selection.{Style.RESET_ALL}")
            return None
    except ValueError:
        print(f"{Fore.RED}Please enter a valid number.{Style.RESET_ALL}")
        return None

#################################################################################
#                              CORE OPERATIONS                                   #
#################################################################################
"""
This section implements the core operations of the application:
- Synchronizing folders
- Running tests
- Crawling URLs
- Extracting content
- Running the full workflow
"""

def sync_folders():
    """Sync categories to directory structure
    
    Runs the sync_categories.py script to ensure the output directory structure
    matches the categories defined in the configuration file.
    
    Returns:
        bool: True if synchronization was successful, False otherwise
    """
    return run_command(
        ["python3", "tools/sync_categories.py"],
        "Category sync"
    )

def run_tests():
    """Run crawler tests
    
    Executes the full test suite for all crawlers.
    
    Returns:
        bool: True if tests completed successfully, False otherwise
    """
    print(f"{Fore.YELLOW}Running full crawler test suite...{Style.RESET_ALL}")
    
    # Directly run full test suite with all crawlers
    command = [
        "python3", "src/tests/test_crawler.py",
        "--full",
        "--report",
        "--output-dir", "output/test_urls"
    ]
    
    print(f"{Fore.CYAN}Executing: {' '.join(command)}{Style.RESET_ALL}")
    return run_command(command, f"Full crawler test suite")

def run_extraction_tests():
    """Run extraction tests
    
    Executes the extraction test suite to verify content extraction is working properly.
    
    Returns:
        bool: True if tests completed successfully, False otherwise
    """
    print(f"{Fore.YELLOW}Running extraction test suite...{Style.RESET_ALL}")
    
    # Run the full test suite with report generation enabled
    command = ["python3", "src/tests/test_extractor.py", "--report"]
    
    print(f"{Fore.CYAN}Executing: {' '.join(command)}{Style.RESET_ALL}")
    return run_command(command, "Extraction test suite")

def crawl_urls(categories=None, resume=False):
    """Run the URL crawl process
    
    Executes the master crawler to collect URLs from websites based on specified categories.
    
    Args:
        categories: List of specific categories to crawl, or None for all
        resume: Whether to resume from a previous crawl state
        
    Returns:
        bool: True if crawling completed successfully, False otherwise
    """
    command = [
        "python3", "src/crawlers/master_crawler_controller.py",
        "--max-urls", str(CONFIG["urls_per_category"]),
        "--output-dir", CONFIG["urls_dir"]
    ]
    
    if resume:
        command.append("--resume")
    
    if categories and len(categories) == 1:
        command.extend(["--category", categories[0]])
    elif categories and len(categories) > 1:
        command.append("--categories")
        command.extend(categories)
    
    return run_command(
        command,
        f"URL crawling for {', '.join(categories) if categories else 'all categories'}"
    )

def extract_content(resume=True):
    """Run the content extraction process
    
    Executes the article crawler to process collected URLs and extract article content.
    Automatically processes all categories and stops when complete.
    
    Args:
        resume: Whether to resume from checkpoint (True) or restart (False)
        
    Returns:
        bool: True if extraction completed successfully, False otherwise
    """
    command = [
        "bash", "scripts/run_article_crawler.sh"
    ]
    
    if not resume:
        command.append("--reset-checkpoint")
    
    return run_command(
        command,
        "Article extraction (all categories)"
    )

def run_full_workflow(categories=None, resume=False):
    """Run the complete workflow (sync, crawl, extract)
    
    Executes the entire data collection pipeline in sequence:
    1. Sync folders to ensure proper directory structure
    2. Crawl URLs from websites
    3. Extract content from the collected URLs
    
    Args:
        categories: List of specific categories to process, or None for all
        resume: Whether to resume from previous state
        
    Returns:
        bool: True if the entire workflow completed successfully, False otherwise
    """
    print(f"{Fore.GREEN}Starting full workflow...{Style.RESET_ALL}")
    
    if not sync_folders():
        print(f"{Fore.YELLOW}Warning: Folder sync failed, but continuing with workflow...{Style.RESET_ALL}")
    
    if not crawl_urls(categories, resume):
        print(f"{Fore.RED}URL crawling failed. Stopping workflow.{Style.RESET_ALL}")
        return False
    
    if CONFIG["stop_requested"]:
        return False
    
    return extract_content(categories, resume)

#################################################################################
#                          CONFIGURATION MANAGEMENT                              #
#################################################################################
"""
This section handles configuration settings:
- Displaying and modifying configuration options
- Saving and loading configuration
- Command-line argument parsing
"""

def configure_settings():
    """Configure application settings
    
    Presents a menu of configurable options and allows the user to change them.
    Changes are applied immediately in memory, and saved when the program exits.
    
    The settings include:
    - URLs per category
    - Number of workers for extraction
    - Input and output directories
    - Configuration file paths
    """
    print_header()
    print(f"{Fore.GREEN}Settings Configuration{Style.RESET_ALL}")
    print_status()
    
    print(f"{Fore.CYAN}Select a setting to change:{Style.RESET_ALL}")
    print("  1. URLs per category")
    print("  2. Extract workers")
    print("  3. Output directory")
    print("  4. URLs directory")
    print("  5. Categories file path")
    print("  0. Return to main menu")
    
    try:
        choice = int(input(f"\n{Fore.YELLOW}Select an option (0-5): {Style.RESET_ALL}"))
        
        if choice == 0:
            return
        elif choice == 1:
            try:
                CONFIG["urls_per_category"] = int(input(f"Enter URLs per category (current: {CONFIG['urls_per_category']}): "))
                print(f"{Fore.GREEN}URLs per category updated to {CONFIG['urls_per_category']}{Style.RESET_ALL}")
            except ValueError:
                print(f"{Fore.RED}Please enter a valid number.{Style.RESET_ALL}")
        elif choice == 2:
            try:
                CONFIG["extract_workers"] = int(input(f"Enter extract workers (current: {CONFIG['extract_workers']}): "))
                print(f"{Fore.GREEN}Extract workers updated to {CONFIG['extract_workers']}{Style.RESET_ALL}")
            except ValueError:
                print(f"{Fore.RED}Please enter a valid number.{Style.RESET_ALL}")
        elif choice == 3:
            CONFIG["output_dir"] = input(f"Enter output directory (current: {CONFIG['output_dir']}): ")
            print(f"{Fore.GREEN}Output directory updated to {CONFIG['output_dir']}{Style.RESET_ALL}")
        elif choice == 4:
            CONFIG["urls_dir"] = input(f"Enter URLs directory (current: {CONFIG['urls_dir']}): ")
            print(f"{Fore.GREEN}URLs directory updated to {CONFIG['urls_dir']}{Style.RESET_ALL}")
        elif choice == 5:
            CONFIG["categories_file"] = input(f"Enter categories file path (current: {CONFIG['categories_file']}): ")
            print(f"{Fore.GREEN}Categories file updated to {CONFIG['categories_file']}{Style.RESET_ALL}")
        else:
            print(f"{Fore.RED}Invalid selection.{Style.RESET_ALL}")
        
        input(f"\n{Fore.GREEN}Press Enter to continue...{Style.RESET_ALL}")
        configure_settings()  # Return to settings menu
        
    except ValueError:
        print(f"{Fore.RED}Please enter a valid number.{Style.RESET_ALL}")
        input(f"\n{Fore.GREEN}Press Enter to continue...{Style.RESET_ALL}")
        configure_settings()  # Return to settings menu

def save_config():
    """Save the current configuration
    
    Writes the current configuration settings to a JSON file,
    excluding runtime-specific variables like running_process.
    
    This allows settings to persist between program runs.
    """
    config_to_save = {k: v for k, v in CONFIG.items() if k not in ["running_process", "stop_requested"]}
    try:
        os.makedirs(os.path.dirname("config/cli_config.json"), exist_ok=True)
        with open("config/cli_config.json", "w", encoding="utf-8") as f:
            json.dump(config_to_save, f, indent=4)
    except Exception as e:
        print(f"{Fore.RED}Failed to save configuration: {str(e)}{Style.RESET_ALL}")

def load_config():
    """Load saved configuration if available
    
    Reads configuration settings from a JSON file if it exists,
    and updates the runtime configuration with those values.
    
    This restores settings from previous runs of the program.
    """
    try:
        if os.path.exists("config/cli_config.json"):
            with open("config/cli_config.json", "r", encoding="utf-8") as f:
                saved_config = json.load(f)
                for key, value in saved_config.items():
                    if key in CONFIG:
                        CONFIG[key] = value
            print(f"{Fore.GREEN}Loaded saved configuration.{Style.RESET_ALL}")
    except Exception as e:
        print(f"{Fore.YELLOW}Could not load configuration: {str(e)}{Style.RESET_ALL}")

def parse_command_line():
    """Parse command line arguments
    
    Processes command-line arguments that can override configuration settings.
    This allows for quick adjustment of settings without changing the config file.
    
    Supported arguments:
    --urls-per-category: Number of URLs to collect per category
    --extract-workers: Number of concurrent extract workers
    --output-dir: Directory for output articles
    --urls-dir: Directory for URL files
    """
    parser = argparse.ArgumentParser(description="Data Collection CLI")
    parser.add_argument("--urls-per-category", type=int, help="Target URLs per category")
    parser.add_argument("--extract-workers", type=int, help="Number of extract workers")
    parser.add_argument("--output-dir", help="Output directory for articles")
    parser.add_argument("--urls-dir", help="Directory for URL files")
    
    args = parser.parse_args()
    
    # Update CONFIG with any command line arguments
    if args.urls_per_category:
        CONFIG["urls_per_category"] = args.urls_per_category
    if args.extract_workers:
        CONFIG["extract_workers"] = args.extract_workers
    if args.output_dir:
        CONFIG["output_dir"] = args.output_dir
    if args.urls_dir:
        CONFIG["urls_dir"] = args.urls_dir

#################################################################################
#                               MAIN MENU                                        #
#################################################################################
"""
This section implements the main application menu:
- Displaying menu options
- Handling user input
- Routing to appropriate functions based on selection
"""

def main_menu():
    """Display the main menu and handle user input
    
    This is the central function of the CLI, presenting the main menu and
    routing user requests to the appropriate handlers.
    
    The main menu provides options for:
    - Running individual components
    - Testing crawlers
    - Synchronizing folders
    - Configuring settings
    """
    while True:
        print_header()
        print(f"{Fore.GREEN}Main Menu:{Style.RESET_ALL}")
        print("  1. Crawl URLs only")
        print("  2. Extract articles from URLs")
        print("  3. Test crawlers")
        print("  4. Test extraction")
        print("  5. Sync categories and folders")
        print("  6. Configure settings")
        print("  0. Exit")
        
        print_status()
        
        try:
            choice = int(input(f"{Fore.YELLOW}Select an option (0-6): {Style.RESET_ALL}"))
            
            # Reset stop flag when starting a new operation
            CONFIG["stop_requested"] = False
            
            if choice == 0:
                print(f"{Fore.GREEN}Exiting program. Goodbye!{Style.RESET_ALL}")
                sys.exit(0)
            elif choice == 1:  # Crawl URLs only
                categories = select_categories()
                if categories is not None:
                    crawl_urls(categories, resume=False)
            elif choice == 2:  # Extract articles from URLs
                print(f"{Fore.CYAN}Starting article extraction for all categories.{Style.RESET_ALL}")
                print(f"{Fore.CYAN}This will process all URL files and stop when complete.{Style.RESET_ALL}")
                resume = input(f"{Fore.YELLOW}Resume from last checkpoint? (Y/n): {Style.RESET_ALL}").lower() != 'n'
                extract_content(resume=resume)
            elif choice == 3:  # Test crawlers
                run_tests()
            elif choice == 4:  # Test extraction
                run_extraction_tests()
            elif choice == 5:  # Sync folders
                sync_folders()
            elif choice == 6:  # Configure settings
                configure_settings()
            else:
                print(f"{Fore.RED}Invalid selection. Please enter a number between 0 and 6.{Style.RESET_ALL}")
            
            if not CONFIG["stop_requested"]:
                input(f"\n{Fore.GREEN}Press Enter to return to main menu...{Style.RESET_ALL}")
                
        except ValueError:
            print(f"{Fore.RED}Please enter a valid number.{Style.RESET_ALL}")
            input(f"\n{Fore.GREEN}Press Enter to continue...{Style.RESET_ALL}")
        except Exception as e:
            print(f"{Fore.RED}An error occurred: {str(e)}{Style.RESET_ALL}")
            print(traceback.format_exc())
            input(f"\n{Fore.GREEN}Press Enter to continue...{Style.RESET_ALL}")

if __name__ == "__main__":
    try:
        # First load saved config
        load_config()
        # Then override with command line arguments if provided
        parse_command_line()
        
        # Run initial folder sync
        print(f"{Fore.GREEN}Running initial folder sync...{Style.RESET_ALL}")
        sync_folders()
        
        # Start the application
        main_menu()
    except KeyboardInterrupt:
        print(f"\n{Fore.YELLOW}Program interrupted. Exiting...{Style.RESET_ALL}")
        sys.exit(0)
    finally:
        # Save configuration on exit
        save_config()
