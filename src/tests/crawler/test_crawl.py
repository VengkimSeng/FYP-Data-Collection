import time
import inspect
from src.tests.crawler.test_utils import import_crawler_module, TestResult, logger
from src.tests.crawler.test_sources import run_source_urls_test
from src.utils.chrome_setup import setup_chrome_driver

def run_crawl_minimal_test(crawler_name: str, category: str, max_urls: int = 2) -> TestResult:
    """Test minimal crawling to make sure it returns some URLs."""
    result = TestResult(f"Minimal crawl test for {crawler_name} - {category}")
    
    try:
        # First check we can get source URLs
        source_test = run_source_urls_test(crawler_name, category)
        if not source_test.success:
            return result.set_failure(Exception(source_test.message), f"Source URL test prerequisite failed")
        
        # Import the crawler module
        module, module_path = import_crawler_module(crawler_name)
        result.module_path = module_path
        
        if not module:
            return result.set_failure(Exception("Module import failed"), f"Could not import {crawler_name} crawler")
        
        # Get the first source URL
        source_url = source_test.data['sources'][0]
        
        # Get function signature to identify proper parameter names
        sig = inspect.signature(module.crawl_category)
        param_names = list(sig.parameters.keys())
        
        # Prepare arguments based on crawler type and function signature
        crawl_args = {}
        
        # First param is usually URL but might have different names
        url_param_name = param_names[0] if param_names else 'url'
        crawl_args[url_param_name] = source_url
        
        # Second param is usually category
        if len(param_names) > 1:
            crawl_args[param_names[1]] = category
        
        # Add appropriate limit parameter based on crawler
        if crawler_name == "rfanews" or crawler_name == "rfa":
            crawl_args['max_clicks'] = 1
        elif crawler_name == "postkhmer":
            crawl_args['max_click'] = 1
        elif crawler_name == "kohsantepheapdaily" or crawler_name == "kohsantepheap":
            crawl_args['max_scroll'] = 1
        else:
            crawl_args['max_pages'] = 1
        
        # Call the function
        start_time = time.time()
        urls = module.crawl_category(**crawl_args)
        result.duration = time.time() - start_time
        
        # Check results
        if urls and isinstance(urls, (list, set)) and len(urls) > 0:
            result.set_success(f"Successfully crawled {len(urls)} URLs")
            result.data['url_count'] = len(urls)
            result.data['sample_urls'] = list(urls)[:3]  # Save up to 3 sample URLs
        else:
            result.set_failure(Exception(f"No valid URLs returned: {type(urls)}"), 
                              f"Crawler returned no valid URLs")
        
        return result
    except Exception as e:
        return result.set_failure(e)
