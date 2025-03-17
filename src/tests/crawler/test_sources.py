import time
from src.utils.source_manager import get_source_urls
from src.tests.crawler.test_utils import TestResult, logger

def run_source_urls_test(crawler_name: str, category: str) -> TestResult:
    """Test if source URLs can be retrieved for the crawler and category."""
    result = TestResult(f"Source URLs for {crawler_name} - {category}")
    
    try:
        start_time = time.time()
        sources = get_source_urls(category, crawler_name)
        result.duration = time.time() - start_time
        
        if sources and len(sources) > 0:
            result.set_success(f"Found {len(sources)} source URLs")
            result.data['sources'] = sources
        else:
            result.set_failure(Exception("No sources found"), 
                              f"No source URLs found for {crawler_name} - {category}")
        
        return result
    except Exception as e:
        return result.set_failure(e)
