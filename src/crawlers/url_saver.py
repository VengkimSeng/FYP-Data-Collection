"""
URL Saver Module

This module provides standardized functions for saving and loading URLs across different crawler scripts.
It supports saving URLs in both TXT and JSON formats, with options for filtering and deduplication.
"""

import os
import json
import logging
from typing import Set, List, Dict, Optional, Union, Iterable

# Configure logging
logger = logging.getLogger(__name__)

# Rename this to avoid name conflict when imported
def save_urls_to_file(
    urls: Iterable[str], 
    output_path: str, 
    format_type: str = "json",
    ensure_ascii: bool = False,
    indent: int = 4,
    sort_urls: bool = True
) -> bool:
    """
    Save URLs to a file in either JSON or TXT format.
    
    Args:
        urls: Collection of URLs to save
        output_path: Path where the file will be saved
        format_type: File format, either "json" or "txt" (default: "json")
        ensure_ascii: For JSON, whether to escape non-ASCII characters (default: False)
        indent: For JSON, number of spaces for indentation (default: 4)
        sort_urls: Whether to sort URLs alphabetically before saving (default: True)
        
    Returns:
        bool: True if save was successful, False otherwise
    """
    try:
        # Create directory if it doesn't exist
        os.makedirs(os.path.dirname(output_path) or ".", exist_ok=True)
        
        # Ensure we have a set to remove duplicates
        unique_urls = list(set(urls))
        
        # Sort URLs if requested
        if sort_urls:
            unique_urls.sort()
        
        # Save the file in the requested format
        if format_type.lower() == "json":
            with open(output_path, "w", encoding="utf-8") as f:
                json.dump(unique_urls, f, ensure_ascii=ensure_ascii, indent=indent)
        elif format_type.lower() == "txt":
            with open(output_path, "w", encoding="utf-8") as f:
                for url in unique_urls:
                    f.write(f"{url}\n")
        else:
            logger.error(f"Unsupported file format: {format_type}")
            return False
            
        logger.info(f"Saved {len(unique_urls)} URLs to {output_path}")
        return True
        
    except Exception as e:
        logger.error(f"Error saving URLs to {output_path}: {e}")
        return False

def save_urls_to_multiple_formats(
    urls: Iterable[str],
    base_path: str,
    formats: List[str] = ["json", "txt"],
    sort_urls: bool = True
) -> Dict[str, bool]:
    """
    Save URLs to multiple file formats.
    
    Args:
        urls: Collection of URLs to save
        base_path: Base path for the output files (without extension)
        formats: List of formats to save (default: ["json", "txt"])
        sort_urls: Whether to sort URLs alphabetically before saving (default: True)
        
    Returns:
        Dict[str, bool]: Dictionary with format as key and success status as value
    """
    results = {}
    for fmt in formats:
        path = f"{base_path}.{fmt}"
        results[fmt] = save_urls_to_file(
            urls=urls,
            output_path=path,
            format_type=fmt,
            sort_urls=sort_urls
        )
    return results

def save_urls_with_progress(
    urls: Iterable[str],
    category: str,
    base_folder: str,
    progress_info: Optional[Dict] = None
) -> Dict:
    """
    Save URLs with progress information for resumable crawling.
    
    Args:
        urls: Collection of URLs to save
        category: Category name (used in filenames)
        base_folder: Base folder to save files in
        progress_info: Dictionary containing progress information
        
    Returns:
        Dict: Updated progress information
    """
    # Create necessary folders
    os.makedirs(base_folder, exist_ok=True)
    os.makedirs(os.path.join(base_folder, "filtered"), exist_ok=True)
    
    # Prepare file paths
    urls_file = os.path.join(base_folder, f"{category}_urls.json")
    progress_file = os.path.join(base_folder, f"{category}_progress.json")
    
    # Create or update progress info
    if progress_info is None:
        progress_info = {"unique_urls": [], "pages_scraped": 0}
    
    # Update URLs in progress info
    progress_info["unique_urls"] = list(set(urls))
    
    # Save URLs to file
    save_urls_to_file(urls, urls_file)
    
    # Save progress information
    try:
        with open(progress_file, "w", encoding="utf-8") as f:
            json.dump(progress_info, f, ensure_ascii=False, indent=4)
        logger.info(f"Progress saved to {progress_file}")
    except Exception as e:
        logger.error(f"Error saving progress to {progress_file}: {e}")
    
    return progress_info

def load_urls_from_file(file_path: str) -> List[str]:
    """
    Load URLs from a file (either JSON or TXT).
    
    Args:
        file_path: Path to the file containing URLs
        
    Returns:
        List[str]: List of URLs from the file or empty list if file cannot be read
    """
    try:
        if file_path.lower().endswith('.json'):
            with open(file_path, "r", encoding="utf-8") as f:
                urls = json.load(f)
                return [url for url in urls if url and isinstance(url, str)]
        elif file_path.lower().endswith('.txt'):
            with open(file_path, "r", encoding="utf-8") as f:
                return [line.strip() for line in f if line.strip()]
        else:
            logger.error(f"Unsupported file format for {file_path}")
            return []
    except Exception as e:
        logger.error(f"Error loading URLs from {file_path}: {e}")
        return []

def load_progress(base_folder: str, category: str) -> Dict:
    """
    Load progress information for resumable crawling.
    
    Args:
        base_folder: Base folder where files are saved
        category: Category name (used in filenames)
        
    Returns:
        Dict: Progress information or empty dict if no progress file exists
    """
    progress_file = os.path.join(base_folder, f"{category}_progress.json")
    
    if os.path.exists(progress_file):
        try:
            with open(progress_file, "r", encoding="utf-8") as f:
                progress_data = json.load(f)
                logger.info(f"Loaded progress for {category}: {len(progress_data.get('unique_urls', []))} URLs")
                return progress_data
        except json.JSONDecodeError:
            logger.warning(f"Progress file for {category} is corrupted. Starting fresh.")
    
    logger.info(f"No progress found for {category}. Starting fresh.")
    return {}
