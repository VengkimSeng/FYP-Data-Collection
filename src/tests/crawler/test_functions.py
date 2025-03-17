import time
import inspect
from src.tests.crawler.test_utils import import_crawler_module, TestResult, logger

def run_function_existence_test(crawler_name: str, function_name: str = 'crawl_category') -> TestResult:
    """Test if the crawler has the required functions."""
    result = TestResult(f"Required function '{function_name}' in {crawler_name}")
    
    try:
        module, module_path = import_crawler_module(crawler_name)
        result.module_path = module_path
        
        start_time = time.time()
        if hasattr(module, function_name):
            func = getattr(module, function_name)
            if callable(func):
                # Check function signature
                sig = inspect.signature(func)
                param_names = list(sig.parameters.keys())
                
                if len(param_names) >= 2:  # At minimum needs url and category params
                    result.set_success(f"Found {function_name} function with correct signature")
                    result.data['parameters'] = param_names
                else:
                    result.set_failure(Exception(f"Invalid signature: {param_names}"), 
                                       f"Function {function_name} has invalid signature")
            else:
                result.set_failure(Exception("Not callable"), f"{function_name} exists but is not callable")
        else:
            result.set_failure(Exception(f"Missing function: {function_name}"), 
                               f"{function_name} not found in {crawler_name} module")
        
        result.duration = time.time() - start_time
        return result
    except Exception as e:
        return result.set_failure(e)
