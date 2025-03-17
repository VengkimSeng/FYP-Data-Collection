import time
import traceback
from src.tests.crawler.test_utils import import_crawler_module, TestResult

def run_module_import_test(crawler_name: str) -> TestResult:
    """Test importing the crawler module."""
    result = TestResult(f"Import {crawler_name} module")
    
    try:
        start_time = time.time()
        module, module_path = import_crawler_module(crawler_name)
        result.duration = time.time() - start_time
        
        if module:
            result.module_path = module_path
            result.set_success(f"Successfully imported {crawler_name} crawler module")
        else:
            result.set_failure(Exception(f"Failed to import module"), f"Could not import {crawler_name} crawler module")
        
        return result
    except Exception as e:
        return result.set_failure(e)
