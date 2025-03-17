import inspect
import time
from typing import List, Set, Dict, Any, Optional
from src.tests.crawler.test_utils import import_crawler_module, TestResult, logger

def run_filter_urls_test(crawler_name: str) -> TestResult:
    """
    Test URL filtering functionality with crawler-specific handling.
    
    This function dispatches to crawler-specific test functions based on crawler name.
    """
    result = TestResult(f"URL filtering test for {crawler_name}")
    
    # Map crawler names to specific test functions
    filter_test_map = {
        "btv": test_btv_filter,
        "dapnews": test_dapnews_filter,
        "kohsantepheap": test_kohsantepheap_filter,
        "kohsantepheapdaily": test_kohsantepheap_filter,  # Same as kohsantepheap
        "postkhmer": test_postkhmer_filter,
        "rfanews": test_rfanews_filter,
        "rfa": test_rfanews_filter,  # Same as rfanews
        "sabaynews": test_sabay_filter
    }
    
    # Get the appropriate test function
    test_func = filter_test_map.get(crawler_name.lower())
    
    if test_func:
        return test_func(crawler_name)
    else:
        # Fallback to generic test if no specific handler
        return generic_filter_test(crawler_name)

def generic_filter_test(crawler_name: str) -> TestResult:
    """
    Generic filter test for crawlers without specific test implementations.
    """
    result = TestResult(f"URL filtering test for {crawler_name}")
    
    try:
        module, module_path = import_crawler_module(crawler_name)
        result.module_path = module_path
        
        if not module:
            return result.set_failure(Exception("Module import failed"), f"Could not import {crawler_name} crawler")
        
        # Find the filter function
        filter_func = None
        for name, func in inspect.getmembers(module, inspect.isfunction):
            if 'filter' in name.lower() and 'url' in name.lower():
                filter_func = func
                break
        
        if not filter_func:
            return result.set_failure(Exception("No filter function found"), 
                                   f"No URL filtering function found in {crawler_name} module")
        
        # Prepare test URLs
        test_urls = [
            f"https://{crawler_name}.com/good/article1",
            f"https://{crawler_name}.com/category/bad",
            f"https://{crawler_name}.com/good/article2",
            f"https://{crawler_name}.com/tag/bad",
        ]
        
        # Call the function with basic parameters
        start_time = time.time()
        filtered_urls = filter_func(test_urls, "test_category")
        result.duration = time.time() - start_time
        
        # Check if it filtered correctly
        if filtered_urls and len(filtered_urls) < len(test_urls) and len(filtered_urls) > 0:
            result.set_success(f"URL filtering works: {len(test_urls)} → {len(filtered_urls)}")
            result.data['filtered_count'] = len(filtered_urls)
            result.data['original_count'] = len(test_urls)
        else:
            if not filtered_urls or len(filtered_urls) == 0:
                result.set_failure(Exception("All URLs were filtered"), 
                                f"Filtering removed all URLs (too aggressive)")
            else:
                result.set_failure(Exception("No URLs were filtered"), 
                                f"Filtering didn't remove any URLs")
        
        return result
        
    except Exception as e:
        return result.set_failure(e)

def test_btv_filter(crawler_name: str) -> TestResult:
    """BTV-specific filter test."""
    result = TestResult(f"URL filtering test for {crawler_name}")
    
    try:
        module, module_path = import_crawler_module(crawler_name)
        result.module_path = module_path
        
        if not module:
            return result.set_failure(Exception("Module import failed"), f"Could not import {crawler_name} crawler")
        
        # BTV uses filter_btv_urls function that takes a set and category
        filter_func = getattr(module, "filter_btv_urls", None)
        if not filter_func:
            return result.set_failure(Exception("filter_btv_urls function not found"), 
                                   f"Required filtering function not found")
        
        # Prepare test URLs specifically for BTV
        test_urls = set([
            "https://btv.com.kh/article/123456",  # Good URL
            "https://btv.com.kh/category/sport",  # Bad URL (category page)
            "https://btv.com.kh/article/789012",  # Good URL
            "https://btv.com.kh/tag/news",        # Bad URL (tag page)
            "https://other-domain.com/article/1"  # Bad URL (wrong domain)
        ])
        
        # Run the filter function
        start_time = time.time()
        filtered_urls = filter_func(test_urls, "sport")
        result.duration = time.time() - start_time
        
        # Check results
        if isinstance(filtered_urls, (list, set)) and len(filtered_urls) == 2:
            result.set_success(f"URL filtering works: {len(test_urls)} → {len(filtered_urls)}")
            result.data['filtered_count'] = len(filtered_urls)
            result.data['original_count'] = len(test_urls)
        else:
            if isinstance(filtered_urls, (list, set)) and len(filtered_urls) == 0:
                result.set_failure(Exception("All URLs were filtered"), 
                                "BTV filter removed all URLs (too aggressive)")
            elif isinstance(filtered_urls, (list, set)) and len(filtered_urls) > 2:
                result.set_failure(Exception("Not enough URLs were filtered"), 
                                "BTV filter didn't remove enough URLs")
            else:
                result.set_failure(Exception(f"Invalid return: {filtered_urls}"), 
                                f"BTV filter returned unexpected result")
        
        return result
    except Exception as e:
        return result.set_failure(e)

def test_dapnews_filter(crawler_name: str) -> TestResult:
    """DapNews-specific filter test."""
    result = TestResult(f"URL filtering test for {crawler_name}")
    
    try:
        module, module_path = import_crawler_module(crawler_name)
        result.module_path = module_path
        
        if not module:
            return result.set_failure(Exception("Module import failed"), f"Could not import {crawler_name} crawler")
            
        # DapNews uses filter_dapnews_urls function
        filter_func = getattr(module, "filter_dapnews_urls", None)
        if not filter_func:
            return result.set_failure(Exception("filter_dapnews_urls function not found"), 
                                  f"Required filtering function not found")
        
        # Prepare test URLs specifically for DapNews
        test_urls = set([
            "https://dap-news.com/2023/02/15/123456/",  # Good URL with date pattern
            "https://dap-news.com/category/sport/",     # Bad URL (category page)
            "https://dap-news.com/2023/01/10/789012/",  # Good URL with date pattern
            "https://dap-news.com/tag/news/",           # Bad URL (tag page)
            "https://other-domain.com/article/1"        # Bad URL (wrong domain)
        ])
        
        # Run the filter function
        start_time = time.time()
        filtered_urls = filter_func(test_urls, "sport")
        result.duration = time.time() - start_time
        
        # Check results - expecting 2 URLs to pass (the ones with date patterns)
        if isinstance(filtered_urls, (list, set)) and 0 < len(filtered_urls) < len(test_urls):
            result.set_success(f"URL filtering works: {len(test_urls)} → {len(filtered_urls)}")
            result.data['filtered_count'] = len(filtered_urls)
            result.data['original_count'] = len(test_urls)
        else:
            if isinstance(filtered_urls, (list, set)) and len(filtered_urls) == 0:
                result.set_failure(Exception("All URLs were filtered"), 
                                "DapNews filter removed all URLs (too aggressive)")
            elif isinstance(filtered_urls, (list, set)) and len(filtered_urls) >= len(test_urls):
                result.set_failure(Exception("No URLs were filtered"), 
                                "DapNews filter didn't remove any URLs")
            else:
                result.set_failure(Exception(f"Invalid return: {filtered_urls}"), 
                                f"DapNews filter returned unexpected result")
        
        return result
    except Exception as e:
        return result.set_failure(e)

def test_kohsantepheap_filter(crawler_name: str) -> TestResult:
    """Kohsantepheap-specific filter test."""
    result = TestResult(f"URL filtering test for {crawler_name}")
    
    try:
        module, module_path = import_crawler_module(crawler_name)
        result.module_path = module_path
        
        if not module:
            return result.set_failure(Exception("Module import failed"), f"Could not import {crawler_name} crawler")
            
        # Kohsantepheap uses filter_kohsantepheap_urls function
        filter_func = getattr(module, "filter_kohsantepheap_urls", None)
        if not filter_func:
            return result.set_failure(Exception("filter_kohsantepheap_urls function not found"), 
                                  f"Required filtering function not found")
        
        # Prepare test URLs specifically for Kohsantepheap
        test_urls = set([
            "https://kohsantepheapdaily.com.kh/article/123456.html", # Good URL
            "https://kohsantepheapdaily.com.kh/category/sport/",     # Bad URL (category page)
            "https://kohsantepheapdaily.com/article/789012.html",    # Good URL (alternate domain)
            "https://kohsantepheap.com.kh/tag/news/",                # Bad URL (tag page)
            "https://other-domain.com/article/1"                     # Bad URL (wrong domain)
        ])
        
        # Run the filter function
        start_time = time.time()
        filtered_urls = filter_func(test_urls, "sport")
        result.duration = time.time() - start_time
        
        # Check results - expecting 2 URLs to pass (the article URLs)
        if isinstance(filtered_urls, (list, set)) and 0 < len(filtered_urls) < len(test_urls):
            result.set_success(f"URL filtering works: {len(test_urls)} → {len(filtered_urls)}")
            result.data['filtered_count'] = len(filtered_urls)
            result.data['original_count'] = len(test_urls)
        else:
            if isinstance(filtered_urls, (list, set)) and len(filtered_urls) == 0:
                result.set_failure(Exception("All URLs were filtered"), 
                                "Kohsantepheap filter removed all URLs (too aggressive)")
            elif isinstance(filtered_urls, (list, set)) and len(filtered_urls) >= len(test_urls):
                result.set_failure(Exception("No URLs were filtered"), 
                                "Kohsantepheap filter didn't remove any URLs")
            else:
                result.set_failure(Exception(f"Invalid return: {filtered_urls}"), 
                                f"Kohsantepheap filter returned unexpected result")
        
        return result
    except Exception as e:
        return result.set_failure(e)

def test_postkhmer_filter(crawler_name: str) -> TestResult:
    """PostKhmer-specific filter test."""
    result = TestResult(f"URL filtering test for {crawler_name}")
    
    try:
        module, module_path = import_crawler_module(crawler_name)
        result.module_path = module_path
        
        if not module:
            return result.set_failure(Exception("Module import failed"), f"Could not import {crawler_name} crawler")
            
        # PostKhmer uses filter_postkhmer_urls function
        filter_func = getattr(module, "filter_postkhmer_urls", None)
        if not filter_func:
            return result.set_failure(Exception("filter_postkhmer_urls function not found"), 
                                  f"Required filtering function not found")
        
        # Prepare test URLs specifically for PostKhmer
        test_urls = [
            "https://postkhmer.com/sport/123456",        # Good URL
            "https://postkhmer.com/category/sport",      # Bad URL (category page)
            "https://postkhmer.com/politics/789012",     # Good URL
            "https://postkhmer.com/tag/news",            # Bad URL (tag page)
            "https://www.postkhmer.com/sport/456789"     # Good URL (with www)
        ]
        
        # Run the filter function
        start_time = time.time()
        filtered_urls = filter_func(test_urls, "sport")
        result.duration = time.time() - start_time
        
        # Check results - expecting 3 URLs to pass (the ones with /sport/ or /politics/)
        if isinstance(filtered_urls, (list, set)) and 0 < len(filtered_urls) < len(test_urls):
            result.set_success(f"URL filtering works: {len(test_urls)} → {len(filtered_urls)}")
            result.data['filtered_count'] = len(filtered_urls)
            result.data['original_count'] = len(test_urls)
        else:
            if isinstance(filtered_urls, (list, set)) and len(filtered_urls) == 0:
                result.set_failure(Exception("All URLs were filtered"), 
                                "PostKhmer filter removed all URLs (too aggressive)")
            elif isinstance(filtered_urls, (list, set)) and len(filtered_urls) >= len(test_urls):
                result.set_failure(Exception("No URLs were filtered"), 
                                "PostKhmer filter didn't remove any URLs")
            else:
                result.set_failure(Exception(f"Invalid return: {filtered_urls}"), 
                                f"PostKhmer filter returned unexpected result")
        
        return result
    except Exception as e:
        return result.set_failure(e)

def test_rfanews_filter(crawler_name: str) -> TestResult:
    """RFA News-specific filter test."""
    result = TestResult(f"URL filtering test for {crawler_name}")
    
    try:
        module, module_path = import_crawler_module(crawler_name)
        result.module_path = module_path
        
        if not module:
            return result.set_failure(Exception("Module import failed"), f"Could not import {crawler_name} crawler")
            
        # RFA uses filter_article_urls function that needs base_domain
        filter_func = getattr(module, "filter_article_urls", None)
        if not filter_func:
            return result.set_failure(Exception("filter_article_urls function not found"), 
                                  f"Required filtering function not found")
        
        # Prepare test URLs specifically for RFA
        test_urls = [
            "https://www.rfa.org/khmer/news/health/article123.html",    # Good URL
            "https://www.rfa.org/khmer/category/health",                # Bad URL (category page)
            "https://www.rfa.org/khmer/news/health/article456.html",    # Good URL
            "https://www.rfa.org/khmer/tag/health",                     # Bad URL (tag page)
            "https://other-domain.org/khmer/article1.html"              # Bad URL (wrong domain)
        ]
        
        # Run the filter function with base_domain parameter
        start_time = time.time()
        filtered_urls = filter_func(test_urls, "rfa.org", "health")
        result.duration = time.time() - start_time
        
        # Check results - expecting 2 URLs to pass (the ones with .html extension)
        if isinstance(filtered_urls, (list, set)) and 0 < len(filtered_urls) < len(test_urls):
            result.set_success(f"URL filtering works: {len(test_urls)} → {len(filtered_urls)}")
            result.data['filtered_count'] = len(filtered_urls)
            result.data['original_count'] = len(test_urls)
        else:
            if isinstance(filtered_urls, (list, set)) and len(filtered_urls) == 0:
                result.set_failure(Exception("All URLs were filtered"), 
                                "RFA filter removed all URLs (too aggressive)")
            elif isinstance(filtered_urls, (list, set)) and len(filtered_urls) >= len(test_urls):
                result.set_failure(Exception("No URLs were filtered"), 
                                "RFA filter didn't remove any URLs")
            else:
                result.set_failure(Exception(f"Invalid return: {filtered_urls}"), 
                                f"RFA filter returned unexpected result")
        
        return result
    except Exception as e:
        return result.set_failure(e)

def test_sabay_filter(crawler_name: str) -> TestResult:
    """Sabay News-specific filter test."""
    result = TestResult(f"URL filtering test for {crawler_name}")
    
    try:
        module, module_path = import_crawler_module(crawler_name)
        result.module_path = module_path
        
        if not module:
            return result.set_failure(Exception("Module import failed"), f"Could not import {crawler_name} crawler")
            
        # Sabay uses filter_sabay_urls function
        filter_func = getattr(module, "filter_sabay_urls", None)
        if not filter_func:
            return result.set_failure(Exception("filter_sabay_urls function not found"), 
                                  f"Required filtering function not found")
        
        # Prepare test URLs specifically for Sabay
        test_urls = set([
            "https://news.sabay.com.kh/article/1234567",      # Good URL
            "https://news.sabay.com.kh/category/sport",       # Bad URL (category page)
            "https://news.sabay.com.kh/article/7890123",      # Good URL
            "https://news.sabay.com.kh/tag/sport",            # Bad URL (tag page)
            "https://other-domain.com/article/1"              # Bad URL (wrong domain)
        ])
        
        # Run the filter function
        start_time = time.time()
        filtered_urls = filter_func(test_urls, "sport")
        result.duration = time.time() - start_time
        
        # Check results - expecting 2 URLs to pass (the ones with /article/)
        if isinstance(filtered_urls, (list, set)) and 0 < len(filtered_urls) < len(test_urls):
            result.set_success(f"URL filtering works: {len(test_urls)} → {len(filtered_urls)}")
            result.data['filtered_count'] = len(filtered_urls)
            result.data['original_count'] = len(test_urls)
        else:
            if isinstance(filtered_urls, (list, set)) and len(filtered_urls) == 0:
                result.set_failure(Exception("All URLs were filtered"), 
                                "Sabay filter removed all URLs (too aggressive)")
            elif isinstance(filtered_urls, (list, set)) and len(filtered_urls) >= len(test_urls):
                result.set_failure(Exception("No URLs were filtered"), 
                                "Sabay filter didn't remove any URLs")
            else:
                result.set_failure(Exception(f"Invalid return: {filtered_urls}"), 
                                f"Sabay filter returned unexpected result")
        
        return result
    except Exception as e:
        return result.set_failure(e)
