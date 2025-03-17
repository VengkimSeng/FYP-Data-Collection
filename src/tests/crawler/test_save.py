import os
import time
import json
from src.utils.log_utils import get_crawler_logger
from src.utils.incremental_saver import IncrementalURLSaver
from src.tests.crawler.test_utils import TestResult, project_root, logger

def run_save_test(crawler_name: str, category: str, output_dir: str = "output/test_urls") -> TestResult:
    """Test saving URLs to disk."""
    result = TestResult(f"URL saving test for {crawler_name} - {category}")
    
    try:
        # Create a saver instance
        output_path = os.path.join(project_root, output_dir)
        os.makedirs(output_path, exist_ok=True)
        
        # Set up logger
        test_logger = get_crawler_logger(f"test_{crawler_name}")
        
        # Create saver
        saver = IncrementalURLSaver(
            output_dir=output_path,
            site_name=crawler_name,
            backup_interval=5,
            logger=test_logger
        )
        
        # Add some test URLs
        start_time = time.time()
        test_urls = [
            f"https://test-{crawler_name}.com/{category}/article1",
            f"https://test-{crawler_name}.com/{category}/article2",
            f"https://test-{crawler_name}.com/{category}/article3"
        ]
        
        added = saver.add_urls(category, test_urls, save_immediately=True)
        result.duration = time.time() - start_time
        
        # Check if URLs were added and saved
        if added > 0:
            # Check if the file exists
            expected_file = os.path.join(output_path, f"{category}.json")
            if os.path.exists(expected_file):
                # Verify file content
                with open(expected_file, 'r', encoding='utf-8') as f:
                    saved_urls = json.load(f)
                    if saved_urls and len(saved_urls) >= len(test_urls):
                        result.set_success(f"Successfully saved {len(test_urls)} URLs to {expected_file}")
                        result.data['saved_file'] = expected_file
                    else:
                        result.set_failure(Exception(f"File has wrong content: {saved_urls}"),
                                         f"Saved file has incorrect content")
            else:
                result.set_failure(Exception(f"File not created: {expected_file}"),
                                 f"URL file was not created")
        else:
            result.set_failure(Exception(f"No URLs added: {added}"),
                             f"Failed to add URLs to saver")
        
        return result
    except Exception as e:
        return result.set_failure(e)
