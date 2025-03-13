#!/usr/bin/env python3
"""
Workflow CLI

This script provides a command-line interface for running the complete article extraction workflow,
with support for running specific steps of the process.

Usage:
    python run_workflow_cli.py [command] [options]
    
Commands:
    sync        Sync categories.json to Scrape_urls directory
    crawl       Run the URL crawler to collect article URLs
    extract     Extract content from article URLs
    all         Run the complete workflow (sync + crawl + extract)
"""

import os
import sys
import argparse
import subprocess
import logging
import time
import platform
from datetime import datetime

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
    handlers=[
        logging.FileHandler("workflow.log"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger("workflow")

# Determine the correct python command based on platform
PYTHON_CMD = "python3" if platform.system() == "Darwin" else "python"

def check_dependencies():
    """Check if required dependencies are installed."""
    try:
        import psutil
        logger.info("psutil module is already installed")
        return True
    except ImportError:
        logger.warning("Required module 'psutil' is not installed")
        logger.warning("Installing required dependencies...")
        
        try:
            # Try to install psutil
            subprocess.run([PYTHON_CMD, "-m", "pip", "install", "psutil"], check=True)
            logger.info("Successfully installed psutil")
            return True
        except Exception as e:
            logger.error(f"Failed to install psutil: {e}")
            logger.error("Please install dependencies manually: pip install psutil")
            return False

def run_command(command, description):
    """Run a command with logging and error handling."""
    logger.info(f"Starting: {description}")
    logger.info(f"Command: {command}")
    
    try:
        # Replace 'python' with the correct Python command for the platform
        if command.startswith("python "):
            command = f"{PYTHON_CMD} {command[7:]}"
        elif command.startswith("python3 "):
            command = f"{PYTHON_CMD} {command[8:]}"
        
        # Add the project root to PYTHONPATH to fix import issues
        project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        env = os.environ.copy()
        if 'PYTHONPATH' in env:
            env['PYTHONPATH'] = f"{project_root}:{env['PYTHONPATH']}"
        else:
            env['PYTHONPATH'] = project_root
        
        result = subprocess.run(command, shell=True, check=True, env=env)
        logger.info(f"Completed: {description}")
        return True
    except subprocess.CalledProcessError as e:
        logger.error(f"Command failed with exit code {e.returncode}: {command}")
        return False
    except Exception as e:
        logger.error(f"Failed to execute {description}: {e}")
        return False

def cmd_sync(args):
    """Sync categories.json to Scrape_urls directory."""
    print("Syncing categories to Scrape_urls directory")
    # Fix: pass a string command and a description
    script_path = os.path.join(os.path.dirname(__file__), "sync_categories.py")
    run_command(f"{PYTHON_CMD} {script_path}", "Syncing categories")

def cmd_crawl(args):
    """Run the URL crawler to collect article URLs."""
    # Fix the path to the master_crawler_controller.py script
    crawler_script = os.path.join(os.path.dirname(os.path.dirname(__file__)), 
                                 "src/crawlers/master_crawler_controller.py")
    
    # Change output directory from Scrape_urls to output/urls
    output_dir = os.path.join("output", "urls")
    os.makedirs(output_dir, exist_ok=True)
    
    return run_command(
        f"{PYTHON_CMD} {crawler_script} --urls-per-category {args.urls_per_category} --max-workers {args.max_workers} --output-dir {output_dir}",
        "Running master crawler to collect URLs"
    )

def cmd_extract(args):
    """Extract content from article URLs."""
    # Fix the path to the article_crawler.py script
    extractor_script = os.path.join(os.path.dirname(os.path.dirname(__file__)), 
                                   "src/extractors/article_crawler.py")
    
    # Change input directory from Scrape_urls to output/urls
    input_dir = os.path.join("output", "urls")
    
    cmd = f"{PYTHON_CMD} {extractor_script} --input-dir {input_dir} --output-dir {args.output_dir} --max-workers {args.extract_workers}"
    
    if args.reset_checkpoint:
        cmd += " --reset-checkpoint"
        
    return run_command(cmd, "Extracting article content")

def cmd_all(args):
    """Run the complete workflow."""
    # Check for required dependencies
    if not check_dependencies():
        logger.error("Missing required dependencies. Please install them and try again.")
        return False
    
    # Create output directory
    os.makedirs(args.output_dir, exist_ok=True)
    
    # Step 1: Sync
    script_path = os.path.join(os.path.dirname(__file__), "sync_categories.py")
    if not run_command(f"{PYTHON_CMD} {script_path}", "Syncing categories"):
        logger.error("Failed to sync categories. Exiting.")
        return False
    
    # Step 2: Crawl
    if not cmd_crawl(args):
        logger.error("Master crawler failed. Continuing with existing URLs.")
    
    # Step 3: Extract
    if not cmd_extract(args):
        logger.error("Article extraction failed")
        return False
    
    logger.info(f"Complete workflow finished. Results saved in {args.output_dir}")
    return True

def main():
    parser = argparse.ArgumentParser(description="Run workflow steps for Khmer news article extraction")
    subparsers = parser.add_subparsers(dest="command", help="Workflow command")
    
    # Common arguments
    common_parser = argparse.ArgumentParser(add_help=False)
    common_parser.add_argument("--output-dir", type=str, 
                              default="output/articles",
                              help="Output directory for articles")
    
    # Sync command
    sync_parser = subparsers.add_parser("sync", parents=[common_parser],
                                       help="Sync categories.json to Scrape_urls directory")
    
    # Crawl command
    crawl_parser = subparsers.add_parser("crawl", parents=[common_parser],
                                        help="Run URL crawler")
    crawl_parser.add_argument("--urls-per-category", type=int, default=2500,
                             help="Target URLs per category (default: 2500)")
    crawl_parser.add_argument("--max-workers", type=int, default=3,
                             help="Maximum crawler workers (default: 3)")
    
    # Extract command
    extract_parser = subparsers.add_parser("extract", parents=[common_parser],
                                          help="Extract article content")
    extract_parser.add_argument("--reset-checkpoint", action="store_true",
                               help="Reset extraction checkpoint")
    extract_parser.add_argument("--extract-workers", type=int, default=6,
                               help="Maximum extraction workers (default: 6)")
    
    # All command (complete workflow)
    all_parser = subparsers.add_parser("all", parents=[common_parser],
                                      help="Run complete workflow")
    all_parser.add_argument("--urls-per-category", type=int, default=2500,
                           help="Target URLs per category (default: 2500)")
    all_parser.add_argument("--max-workers", type=int, default=3,
                           help="Maximum crawler workers (default: 3)")
    all_parser.add_argument("--extract-workers", type=int, default=6,
                           help="Maximum extraction workers (default: 6)")
    all_parser.add_argument("--reset-checkpoint", action="store_true",
                           help="Reset extraction checkpoint")
    
    args = parser.parse_args()
    
    # Map commands to functions
    commands = {
        "sync": cmd_sync,
        "crawl": cmd_crawl,
        "extract": cmd_extract,
        "all": cmd_all
    }
    
    # Execute the requested command
    if args.command in commands:
        if commands[args.command](args):
            return 0
        else:
            return 1
    else:
        parser.print_help()
        return 1

if __name__ == "__main__":
    sys.exit(main())
