import os
import json
import logging
from typing import List, Dict, Optional

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("url_saver")

def save_urls_to_file(urls: List[str], output_path: str, format_type: str = "json", category: Optional[str] = None, **kwargs) -> bool:
    """
    Save URLs to a file in the specified format.
    
    Args:
        urls: List of URLs to save
        output_path: Path to the output file or directory
        format_type: Format type ("json" or "txt")
        category: Category name for organizing URLs (optional)
        **kwargs: Additional arguments passed to the JSON dumper
    
    Returns:
        True if successful, False otherwise
    """
    try:
        # If category is specified, save to the Scrape_urls directory
        if category:
            scrape_dir = "output/urls"
            os.makedirs(scrape_dir, exist_ok=True)
            output_path = os.path.join(scrape_dir, f"{category}.{format_type}")
            
            # If file exists, load existing URLs and merge
            unique_urls = set(urls)
            if os.path.exists(output_path):
                if format_type.lower() == "json":
                    with open(output_path, "r", encoding="utf-8") as f:
                        try:
                            existing_urls = json.load(f)
                            unique_urls.update(existing_urls)
                        except json.JSONDecodeError:
                            logger.warning(f"Could not decode existing file {output_path}, overwriting")
                elif format_type.lower() == "txt":
                    with open(output_path, "r", encoding="utf-8") as f:
                        existing_urls = [line.strip() for line in f if line.strip()]
                        unique_urls.update(existing_urls)
            
            urls = list(unique_urls)
        else:
            # Ensure the directory exists
            os.makedirs(os.path.dirname(output_path) or ".", exist_ok=True)
        
        # Save the URLs
        unique_urls = list(set(urls))
        if format_type.lower() == "json":
            with open(output_path, "w", encoding="utf-8") as f:
                json.dump(unique_urls, f, ensure_ascii=False, indent=4, **kwargs)
        elif format_type.lower() == "txt":
            with open(output_path, "w", encoding="utf-8") as f:
                for url in unique_urls:
                    f.write(f"{url}\n")
                    
        logger.info(f"Saved {len(unique_urls)} URLs to {output_path}")
        return True
        
    except Exception as e:
        logger.error(f"Error saving URLs to {output_path}: {e}")
        return False

def save_urls_by_category(url_dict: Dict[str, List[str]], base_dir: str = "output/urls", format_type: str = "json") -> bool:
    """
    Save URLs organized by category.
    
    Args:
        url_dict: Dictionary of category -> URLs
        base_dir: Base directory for output files (default: Scrape_urls)
        format_type: Format type ("json" or "txt")
    
    Returns:
        True if all categories were saved successfully, False otherwise
    """
    os.makedirs(base_dir, exist_ok=True)
    success = True
    
    for category, urls in url_dict.items():
        output_path = os.path.join(base_dir, f"{category}.{format_type}")
        if not save_urls_to_file(urls, output_path, format_type):
            success = False
            
    return success

# For testing the module directly
if __name__ == "__main__":
    # Example usage
    test_urls = {
        "sport": ["https://example.com/sports/1", "https://example.com/sports/2"],
        "economy": ["https://example.com/economy/1", "https://example.com/economy/2"]
    }
    save_urls_by_category(test_urls)
    logger.info("Test completed")
