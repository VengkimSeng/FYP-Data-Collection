#!/usr/bin/env python3
"""
Test script for the article extractor and scraper systems.

This script runs tests on various components of the article extractor 
to ensure that they work correctly individually and together.
"""

import os
import sys
import unittest
import json
import datetime
import traceback
import importlib.util
from unittest import TestLoader, TextTestRunner, TestSuite, TestResult

# Add the parent directory to Python path for proper imports
current_dir = os.path.dirname(os.path.abspath(__file__))
src_dir = os.path.dirname(current_dir)
project_root = os.path.dirname(src_dir)
sys.path.append(project_root)
sys.path.append(src_dir)

from colorama import Fore, Style, init

# Import test modules - use absolute imports from the directory containing the test files
from src.tests.extractor.test_imports import ImportTests
from src.tests.extractor.test_generic_scraper import GenericScraperTests
from src.tests.extractor.test_utils import CheckpointTests
from src.tests.extractor.test_file_processor import FileProcessorTests
from src.tests.extractor.test_storage import StorageTests
from src.tests.extractor.test_adapter import AdapterTests
from src.tests.extractor.test_browser import BrowserTests
from src.tests.extractor.test_logger import LoggerTests
from src.tests.extractor.test_integration import IntegrationTests

# Import individual scraper tests
from src.tests.extractor.test_btv_scraper import BtvScraperTests
from src.tests.extractor.test_postkhmer_scraper import PostKhmerScraperTests
from src.tests.extractor.test_kohsantepheap_scraper import KohsantepheapScraperTests
from src.tests.extractor.test_dapnews_scraper import DapNewsScraperTests
from src.tests.extractor.test_sabay_scraper import SabayScraperTests
from src.tests.extractor.test_rfa_scraper import RfaScraperTests

# Initialize colorama
init(autoreset=True)

# Map category names to their specific test cases
CATEGORY_TEST_MAP = {
    'sport': {
        'scrapers': [BtvScraperTests, PostKhmerScraperTests, KohsantepheapScraperTests, 
                   DapNewsScraperTests, SabayScraperTests, RfaScraperTests],
        'description': 'Tests for sport category across all scrapers'
    },
    'politic': {
        'scrapers': [BtvScraperTests, PostKhmerScraperTests, KohsantepheapScraperTests, 
                   DapNewsScraperTests, RfaScraperTests],
        'description': 'Tests for politics category across all scrapers'
    },
    'economic': {
        'scrapers': [BtvScraperTests, PostKhmerScraperTests, KohsantepheapScraperTests,
                   DapNewsScraperTests],
        'description': 'Tests for economics category across relevant scrapers'
    },
    # Add more categories as needed
}

# Custom test result class to capture more test details for reporting
class DetailedTestResult(unittest.TextTestResult):
    def __init__(self, *args, **kwargs):
        super(DetailedTestResult, self).__init__(*args, **kwargs)
        self.test_results = []
        self.start_times = {}
        
    def startTest(self, test):
        super(DetailedTestResult, self).startTest(test)
        self.start_times[test] = datetime.datetime.now()
        
    def addSuccess(self, test):
        super(DetailedTestResult, self).addSuccess(test)
        execution_time = (datetime.datetime.now() - self.start_times[test]).total_seconds()
        self.test_results.append({
            'name': test.id(),
            'status': 'PASS',
            'time': execution_time
        })
        
    def addFailure(self, test, err):
        super(DetailedTestResult, self).addFailure(test, err)
        execution_time = (datetime.datetime.now() - self.start_times[test]).total_seconds()
        self.test_results.append({
            'name': test.id(),
            'status': 'FAIL',
            'time': execution_time,
            'error': str(err[1])
        })
        
    def addError(self, test, err):
        super(DetailedTestResult, self).addError(test, err)
        execution_time = (datetime.datetime.now() - self.start_times[test]).total_seconds()
        self.test_results.append({
            'name': test.id(),
            'status': 'ERROR',
            'time': execution_time,
            'error': str(err[1])
        })
        
# Custom test runner to use our detailed results
class DetailedTestRunner(unittest.TextTestRunner):
    def __init__(self, *args, **kwargs):
        kwargs['resultclass'] = DetailedTestResult
        super(DetailedTestRunner, self).__init__(*args, **kwargs)
        
    def run(self, test):
        result = super(DetailedTestRunner, self).run(test)
        return result

def generate_report(results, test_type, category=None):
    """
    Generate a JSON report from test results
    
    Args:
        results: TestResult object with test results
        test_type: Type of test ('all' or 'category')
        category: Category name if test_type is 'category'
        
    Returns:
        report_data: Dictionary containing the report data
    """
    timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    
    report_data = {
        'timestamp': timestamp,
        'test_type': test_type,
        'test_count': results.testsRun,
        'failures': len(results.failures),
        'errors': len(results.errors),
        'success': results.wasSuccessful(),
    }
    
    if category:
        report_data['category'] = category
    
    # Add detailed test results if available
    if hasattr(results, 'test_results'):
        report_data['results'] = results.test_results
        
        # Calculate statistics
        pass_count = sum(1 for r in results.test_results if r['status'] == 'PASS')
        fail_count = sum(1 for r in results.test_results if r['status'] == 'FAIL')
        error_count = sum(1 for r in results.test_results if r['status'] == 'ERROR')
        
        report_data['statistics'] = {
            'pass': pass_count,
            'fail': fail_count,
            'error': error_count,
            'pass_percentage': (pass_count / results.testsRun) * 100 if results.testsRun > 0 else 0
        }
        
    return report_data

def import_report_generator():
    """Import the report generator module using proper path handling."""
    try:
        # First try direct import
        from src.tests.extractor.report_generator import create_direct_markdown_report
        return create_direct_markdown_report
    except ImportError:
        # Next try relative import
        try:
            from tests.extractor.report_generator import create_direct_markdown_report
            return create_direct_markdown_report
        except ImportError:
            # As a last resort, use direct file import
            report_path = os.path.join(current_dir, "extractor", "report_generator.py")
            if not os.path.exists(report_path):
                raise ImportError(f"Report generator not found at {report_path}")
                
            spec = importlib.util.spec_from_file_location("report_generator", report_path)
            module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(module)
            return module.create_direct_markdown_report

def save_report(report_data, category=None):
    """
    Save test report directly to markdown file
    
    Args:
        report_data: Report data dictionary
        category: Optional category name for the filename
        
    Returns:
        report_filename: Name of the saved report file
    """
    # Create report directory if it doesn't exist
    report_dir = os.path.join(project_root, "output", "test_reports")
    os.makedirs(report_dir, exist_ok=True)
    
    # Generate filename with timestamp
    timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    if category:
        md_filename = f"extractor_test_report_{category}_{timestamp}.md"
    else:
        md_filename = f"extractor_test_report_{timestamp}.md"
        
    md_path = os.path.join(report_dir, md_filename)
    
    try:
        # Get the report generator function
        create_direct_markdown_report = import_report_generator()
        
        # Generate markdown content
        markdown_content = create_direct_markdown_report(report_data)
        
        # Write markdown report to file
        with open(md_path, 'w', encoding='utf-8') as f:
            f.write(markdown_content)
            
        print(f"{Fore.GREEN}Test report saved to: {md_path}{Style.RESET_ALL}")
    except Exception as e:
        print(f"{Fore.YELLOW}Could not generate markdown report: {e}{Style.RESET_ALL}")
        print(traceback.format_exc())
    
    return md_filename

def run_all_tests(verbosity=1):
    """
    Run all extractor tests.
    
    Args:
        verbosity: Test output verbosity level
        
    Returns:
        bool: True if all tests passed, False otherwise
    """
    print(f"{Fore.CYAN}==========================================={Style.RESET_ALL}")
    print(f"{Fore.CYAN}     ARTICLE EXTRACTOR TEST SUITE         {Style.RESET_ALL}")
    print(f"{Fore.CYAN}==========================================={Style.RESET_ALL}")
    
    # Create test loader
    loader = TestLoader()
    
    # Create test suite containing all tests from individual test modules
    test_suite = TestSuite()
    
    # Add all test classes
    test_suite.addTest(loader.loadTestsFromTestCase(ImportTests))
    test_suite.addTest(loader.loadTestsFromTestCase(GenericScraperTests))
    test_suite.addTest(loader.loadTestsFromTestCase(CheckpointTests))
    test_suite.addTest(loader.loadTestsFromTestCase(FileProcessorTests))
    test_suite.addTest(loader.loadTestsFromTestCase(StorageTests))
    test_suite.addTest(loader.loadTestsFromTestCase(AdapterTests))
    test_suite.addTest(loader.loadTestsFromTestCase(BrowserTests))
    test_suite.addTest(loader.loadTestsFromTestCase(LoggerTests))
    test_suite.addTest(loader.loadTestsFromTestCase(IntegrationTests))
    
    # Add all scraper tests
    test_suite.addTest(loader.loadTestsFromTestCase(BtvScraperTests))
    test_suite.addTest(loader.loadTestsFromTestCase(PostKhmerScraperTests))
    test_suite.addTest(loader.loadTestsFromTestCase(KohsantepheapScraperTests))
    test_suite.addTest(loader.loadTestsFromTestCase(DapNewsScraperTests))
    test_suite.addTest(loader.loadTestsFromTestCase(SabayScraperTests))
    test_suite.addTest(loader.loadTestsFromTestCase(RfaScraperTests))
    
    # Run the test suite with our detailed runner
    runner = DetailedTestRunner(verbosity=verbosity)
    results = runner.run(test_suite)
    
    # Generate and save report
    report_data = generate_report(results, 'all')
    save_report(report_data)
    
    # Print summary
    print(f"\n{Fore.CYAN}================== TEST SUMMARY =================={Style.RESET_ALL}")
    print(f"{Fore.CYAN}Ran {results.testsRun} tests{Style.RESET_ALL}")
    
    if results.wasSuccessful():
        print(f"{Fore.GREEN}All tests passed!{Style.RESET_ALL}")
        return True
    else:
        print(f"{Fore.RED}Tests failed: {len(results.failures)} failures, {len(results.errors)} errors{Style.RESET_ALL}")
        return False

def run_category_tests(category, verbosity=1):
    """
    Run tests for a specific category.
    
    Args:
        category: Category to test
        verbosity: Test output verbosity level
        
    Returns:
        bool: True if all tests passed, False otherwise
    """
    print(f"{Fore.CYAN}==========================================={Style.RESET_ALL}")
    print(f"{Fore.CYAN}  ARTICLE EXTRACTOR TEST: {category.upper()}  {Style.RESET_ALL}")
    print(f"{Fore.CYAN}==========================================={Style.RESET_ALL}")
    
    # Check if this is a known category
    if category not in CATEGORY_TEST_MAP:
        print(f"{Fore.RED}Unknown category: {category}{Style.RESET_ALL}")
        print(f"{Fore.YELLOW}Available categories: {', '.join(CATEGORY_TEST_MAP.keys())}{Style.RESET_ALL}")
        return False
    
    # Get the test classes for this category
    category_info = CATEGORY_TEST_MAP[category]
    scraper_tests = category_info['scrapers']
    
    # Create test suite for this category
    loader = TestLoader()
    test_suite = TestSuite()
    
    # Always include common tests
    test_suite.addTest(loader.loadTestsFromTestCase(ImportTests))
    test_suite.addTest(loader.loadTestsFromTestCase(GenericScraperTests))
    test_suite.addTest(loader.loadTestsFromTestCase(CheckpointTests))
    
    # Add this category's scraper tests
    for test_class in scraper_tests:
        # Only add methods that have the category name in them
        for method_name in dir(test_class):
            if method_name.startswith('test_') and (category in method_name or 'all_categories' in method_name):
                test_suite.addTest(test_class(method_name))
    
    # Run the test suite with our detailed runner
    runner = DetailedTestRunner(verbosity=verbosity)
    results = runner.run(test_suite)
    
    # Generate and save report
    report_data = generate_report(results, 'category', category)
    save_report(report_data, category)
    
    # Print summary
    print(f"\n{Fore.CYAN}================== TEST SUMMARY =================={Style.RESET_ALL}")
    print(f"{Fore.CYAN}Category: {category}{Style.RESET_ALL}")
    print(f"{Fore.CYAN}Ran {results.testsRun} tests{Style.RESET_ALL}")
    
    if results.wasSuccessful():
        print(f"{Fore.GREEN}All tests passed!{Style.RESET_ALL}")
        return True
    else:
        print(f"{Fore.RED}Tests failed: {len(results.failures)} failures, {len(results.errors)} errors{Style.RESET_ALL}")
        return False

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="Run article extractor tests")
    parser.add_argument("-v", "--verbose", action="store_true",
                        help="Show verbose output")
    parser.add_argument("--category", type=str,
                        help="Test a specific category")
    parser.add_argument("--report", action="store_true",
                       help="Generate and save a detailed test report")
    args = parser.parse_args()
    
    if args.category:
        success = run_category_tests(args.category, verbosity=2 if args.verbose else 1)
    else:
        success = run_all_tests(verbosity=2 if args.verbose else 1)
        
    sys.exit(0 if success else 1)
