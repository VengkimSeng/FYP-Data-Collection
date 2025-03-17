import os
import sys
import time
import json
import traceback
import concurrent.futures
import argparse
import logging
import atexit
import shutil
import inspect
import re
from concurrent.futures import ThreadPoolExecutor
import importlib
from colorama import Fore, Style, init
from typing import Dict, Set, List, Tuple

# Initialize colorama
init(autoreset=True)

# Add project root to path for imports
project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.append(project_root)

# Import shared utilities first
from src.tests.crawler.test_utils import (
    import_crawler_module, 
    import_master_controller,
    TestResult,
    project_root,
    logger
)

from src.utils.chrome_setup import setup_chrome_driver
from src.utils.source_manager import get_source_urls, get_site_categories
from src.utils.incremental_saver import IncrementalURLSaver

# Now we can safely import the test functions
from src.tests.crawler.test_import import run_module_import_test
from src.tests.crawler.test_functions import run_function_existence_test
from src.tests.crawler.test_sources import run_source_urls_test
from src.tests.crawler.test_crawl import run_crawl_minimal_test
from src.tests.crawler.test_save import run_save_test
from src.tests.crawler.test_filter import run_filter_urls_test
from src.tests.crawler.test_master import run_master_controller_test

# Create log directories in output folder (using standardized path)
os.makedirs(os.path.join(project_root, "output", "logs", "crawlers"), exist_ok=True)
os.makedirs(os.path.join(project_root, "output", "logs", "categories"), exist_ok=True)
os.makedirs(os.path.join(project_root, "output", "logs", "tests"), exist_ok=True)

# Set up an exit handler to flush all logs
def exit_handler():
    for handler in logger.handlers:
        handler.flush()
    for handler in logging.root.handlers:
        handler.flush()
    logging.shutdown()

atexit.register(exit_handler)

# Test result tracking
class TestResult:
    """Class to track test results with detailed error information"""
    def __init__(self, test_name: str, module_path: str = None):
        self.test_name = test_name
        self.module_path = module_path
        self.success = False
        self.message = ""
        self.error = None
        self.error_line = None
        self.error_path = None
        self.duration = 0
        self.data = {}  # Store additional test data

    def set_success(self, message: str = "Test passed successfully"):
        self.success = True
        self.message = message
        return self

    def set_failure(self, error, message: str = "Test failed"):
        self.success = False
        self.message = message
        self.error = str(error)
        
        # Extract traceback info for detailed error reporting
        tb = traceback.extract_tb(sys.exc_info()[2])
        for frame in tb:
            # Only include frames from our project code
            if project_root in frame.filename:
                self.error_path = frame.filename
                self.error_line = frame.lineno
                break
        
        return self

    def __str__(self):
        status = "✅ PASS" if self.success else "❌ FAIL"
        result = f"{status} | {self.test_name}"
        if not self.success:
            result += f": {self.message}"
            if self.error_path and self.error_line:
                result += f" at {os.path.relpath(self.error_path, project_root)}:{self.error_line}"
        return result

# Core testing functions
def import_crawler_module(crawler_name: str):
    """Import crawler module dynamically."""
    try:
        # Standardize crawler name format
        crawler_name = crawler_name.lower()
        module_name = f"{crawler_name}_crawler"
        crawler_dir = os.path.join(project_root, "src", "crawlers", "Urls_Crawler")

        # Case-insensitive file matching
        for filename in os.listdir(crawler_dir):
            if filename.lower() == f"{module_name}.py":
                module_path = os.path.join(crawler_dir, filename)
                logger.info(f"Found crawler module at: {module_path}")
                
                # Import the module using spec
                spec = importlib.util.spec_from_file_location(module_name, module_path)
                module = importlib.util.module_from_spec(spec)
                spec.loader.exec_module(module)
                return module, module_path
                
        logger.error(f"Crawler module not found for: {crawler_name}")
        return None, None
        
    except Exception as e:
        logger.error(f"Failed to import {crawler_name} module: {e}")
        return None, None

def import_master_controller():
    """Import master crawler controller module."""
    try:
        module_path = os.path.join(project_root, "src", "crawlers", "master_crawler_controller.py")
        if os.path.exists(module_path):
            # Import the module using spec
            spec = importlib.util.spec_from_file_location("master_controller", module_path)
            module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(module)
            return module, module_path
        else:
            logger.error(f"Master controller module not found at: {module_path}")
            return None, None
    except Exception as e:
        logger.error(f"Failed to import master controller module: {e}")
        return None, None

# Test checklist runner functions
def run_checklist_for_crawler(crawler_name: str, category: str, output_dir: str = "output/test_urls") -> List[TestResult]:
    """Run all tests for a specific crawler and category."""
    results = []
    
    logger.info(f"Running test checklist for {crawler_name} - {category}")
    print(f"\n{Fore.CYAN}Running test checklist for {crawler_name} - {category}{Style.RESET_ALL}")
    
    # Step 1: Module Import Test
    logger.info("=== Step 1: Module Import Test ===")
    print(f"  {Fore.YELLOW}• Step 1: Module Import Test{Style.RESET_ALL}")
    logger.info("  • Checking if crawler module can be imported")
    logger.info("  • Verifying module path exists")
    import_result = run_module_import_test(crawler_name)
    results.append(import_result)
    print(f"    {'✅' if import_result.success else '❌'} {import_result.message}")
    
    if not import_result.success:
        logger.warning(f"Module import failed for {crawler_name}, skipping remaining tests")
        print(f"    {Fore.RED}Module import failed, skipping remaining tests{Style.RESET_ALL}")
        return results
    
    # Step 2: Function Existence Test
    logger.info("=== Step 2: Function Existence Test ===")
    print(f"  {Fore.YELLOW}• Step 2: Function Existence Test{Style.RESET_ALL}")
    logger.info("  • Checking for required 'crawl_category' function")
    logger.info("  • Verifying function signature")
    function_result = run_function_existence_test(crawler_name, 'crawl_category')
    results.append(function_result)
    print(f"    {'✅' if function_result.success else '❌'} {function_result.message}")
    
    if not function_result.success:
        logger.warning(f"Function existence test failed for {crawler_name}, skipping remaining tests")
        print(f"    {Fore.RED}Function test failed, skipping remaining tests{Style.RESET_ALL}")
        return results
    
    # Step 3: Source URLs Test
    logger.info("=== Step 3: Source URLs Test ===")
    print(f"  {Fore.YELLOW}• Step 3: Source URLs Test{Style.RESET_ALL}")
    logger.info("  • Checking if source URLs are available for category")
    logger.info("  • Verifying source configuration in sources.json")
    source_result = run_source_urls_test(crawler_name, category)
    results.append(source_result)
    print(f"    {'✅' if source_result.success else '❌'} {source_result.message}")
    
    if not source_result.success:
        logger.warning(f"Source URL test failed for {crawler_name}-{category}, skipping remaining tests")
        print(f"    {Fore.RED}Source URL test failed, skipping remaining tests{Style.RESET_ALL}")
        return results
    
    # Only continue if previous basic tests passed
    # Step 4: URL Filtering Test
    logger.info("=== Step 4: URL Filtering Test ===")
    print(f"  {Fore.YELLOW}• Step 4: URL Filtering Test{Style.RESET_ALL}")
    logger.info("  • Checking if URL filtering function exists")
    logger.info("  • Testing filtering functionality with sample URLs")
    logger.info("  • Verifying filter correctly removes invalid URLs")
    filter_result = run_filter_urls_test(crawler_name)
    results.append(filter_result)
    print(f"    {'✅' if filter_result.success else '❌'} {filter_result.message}")
    
    # Step 5: Minimal Crawl Test
    logger.info("=== Step 5: Minimal Crawl Test ===")
    print(f"  {Fore.YELLOW}• Step 5: Minimal Crawl Test{Style.RESET_ALL}")
    logger.info("  • Performing a minimal crawl with limited page count")
    logger.info("  • Testing URL extraction from web pages")
    logger.info("  • Verifying crawler returns valid URLs")
    crawl_result = run_crawl_minimal_test(crawler_name, category)
    results.append(crawl_result)
    print(f"    {'✅' if crawl_result.success else '❌'} {crawl_result.message}")
    
    # Step 6: URL Saving Test
    logger.info("=== Step 6: URL Saving Test ===")
    print(f"  {Fore.YELLOW}• Step 6: URL Saving Test{Style.RESET_ALL}")
    logger.info("  • Testing URL saving functionality")
    logger.info("  • Verifying URLs are correctly written to disk")
    logger.info("  • Checking file format and structure")
    save_result = run_save_test(crawler_name, category, output_dir)
    results.append(save_result)
    print(f"    {'✅' if save_result.success else '❌'} {save_result.message}")
    
    # Print summary for this crawler-category
    passed_tests = sum(1 for test in results if test.success)
    total_tests = len(results)
    print(f"  {Fore.CYAN}Summary for {crawler_name}-{category}: {passed_tests}/{total_tests} tests passed{Style.RESET_ALL}")
    
    return results

def run_full_checklist(crawlers: List[str] = None, categories: List[str] = None, 
                      parallel: bool = False, max_workers: int = 2) -> Dict[str, List[TestResult]]:
    """
    Run complete test checklist across all crawlers and categories.
    
    Args:
        crawlers: List of crawlers to test (None = all)
        categories: List of categories to test (None = first available per crawler)
        parallel: Whether to run tests in parallel
        max_workers: Maximum worker threads for parallel execution
    
    Returns:
        Dictionary with test results
    """
    results = {}
    
    # Get available crawlers if not specified
    if crawlers is None:
        crawler_dir = os.path.join(project_root, "src", "crawlers", "Urls_Crawler")
        crawlers = []
        for file in os.listdir(crawler_dir):
            if file.endswith("_crawler.py"):
                crawlers.append(file.replace("_crawler.py", "").lower())
    
    # Master controller test
    logger.info("Starting Master Controller Test")
    logger.info("=== Step 1: Testing master crawler controller ===")
    logger.info("  • Checking if module can be imported")
    logger.info("  • Verifying controller initialization")
    logger.info("  • Testing crawler discovery")
    master_result = run_master_controller_test()
    results["master_controller"] = [master_result]
    
    # Build test tasks
    test_tasks = []
    for crawler in crawlers:
        # Get categories for this crawler
        crawler_categories = categories
        if crawler_categories is None:
            crawler_categories = get_site_categories(crawler)
            if crawler_categories:
                # Just use the first category for testing
                crawler_categories = [crawler_categories[0]]
        
        for category in crawler_categories:
            test_tasks.append((crawler, category))
    
    # Run tests (in parallel or sequentially)
    if parallel and len(test_tasks) > 1:
        logger.info(f"Running {len(test_tasks)} test tasks in parallel with {max_workers} workers")
        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            futures = {
                executor.submit(run_checklist_for_crawler, crawler, category): (crawler, category)
                for crawler, category in test_tasks
            }
            
            for future in concurrent.futures.as_completed(futures):
                crawler, category = futures[future]
                key = f"{crawler}_{category}"
                try:
                    results[key] = future.result()
                except Exception as e:
                    logger.error(f"Error in test task for {key}: {e}")
                    # Create a failure result
                    results[key] = [TestResult(f"Test {crawler}_{category}").set_failure(e, str(e))]
    else:
        # Run tests sequentially
        for crawler, category in test_tasks:
            key = f"{crawler}_{category}"
            logger.info(f"\n=== Testing Crawler: {crawler} with Category: {category} ===")
            results[key] = run_checklist_for_crawler(crawler, category)
    
    return results

def generate_test_report(results: Dict[str, List[TestResult]]) -> str:
    """Generate a markdown report from test results."""
    report = "# Crawler Test Report\n\n"
    
    # Overall summary
    total_tests = sum(len(tests) for tests in results.values())
    passed_tests = sum(sum(1 for test in tests if test.success) for tests in results.values())
    failed_tests = total_tests - passed_tests
    
    report += f"## Summary\n\n"
    report += f"- **Total Tests:** {total_tests}\n"
    report += f"- **Passed:** {passed_tests}\n"
    report += f"- **Failed:** {failed_tests}\n\n"
    
    # Generate success rate for visualization
    success_rate = 100 * passed_tests / total_tests if total_tests > 0 else 0
    report += f"**Success Rate:** {success_rate:.1f}%\n\n"
    
    # Generate progress bar
    progress_bar = "["
    progress_segments = 20
    filled = int(progress_segments * success_rate / 100)
    progress_bar += "=" * filled
    if filled < progress_segments:
        progress_bar += ">" + " " * (progress_segments - filled - 1)
    progress_bar += "]"
    report += f"```\n{progress_bar}\n```\n\n"
    
    # Test results by section
    report += "## Detailed Results\n\n"
    
    for section, tests in results.items():
        # Split section name into crawler and category
        if section == "master_controller":
            section_title = "Master Controller"
        else:
            parts = section.split("_")
            crawler = parts[0]
            category = "_".join(parts[1:]) if len(parts) > 1 else "N/A"
            section_title = f"{crawler.capitalize()} - {category}"
        
        # Calculate stats for this section
        section_total = len(tests)
        section_passed = sum(1 for test in tests if test.success)
        section_success_rate = 100 * section_passed / section_total if section_total > 0 else 0
        
        report += f"### {section_title}\n\n"
        report += f"Success Rate: {section_success_rate:.1f}% ({section_passed}/{section_total})\n\n"
        
        # Table of test results
        report += "| Test | Result | Duration | Message |\n"
        report += "|------|--------|----------|--------|\n"
        
        for test in tests:
            status = "✅ Pass" if test.success else "❌ Fail"
            duration = f"{test.duration:.2f}s" if test.duration else "N/A"
            message = test.message.replace("|", "\\|")  # Escape pipe characters for markdown tables
            report += f"| {test.test_name} | {status} | {duration} | {message} |\n"
        
        report += "\n"
        
        # If there are failed tests, include error details
        failed_tests = [test for test in tests if not test.success]
        if failed_tests:
            report += "#### Error Details\n\n"
            
            for test in failed_tests:
                report += f"**{test.test_name}**\n\n"
                report += f"- Error: {test.error}\n"
                if test.error_path and test.error_line:
                    rel_path = os.path.relpath(test.error_path, project_root)
                    report += f"- Location: {rel_path}:{test.error_line}\n"
                report += "\n"
                
        report += "---\n\n"
    
    # Add timestamp
    timestamp = time.strftime("%Y-%m-%d %H:%M:%S")
    report += f"\n\nReport generated at: {timestamp}\n"
    
    return report

def save_test_report(report: str, output_dir: str = "output/test_reports"):
    """Save the test report to file."""
    os.makedirs(output_dir, exist_ok=True)
    timestamp = time.strftime("%Y%m%d_%H%M%S")
    filename = os.path.join(output_dir, f"crawler_test_report_{timestamp}.md")
    
    with open(filename, "w", encoding="utf-8") as f:
        f.write(report)
    
    print(f"\nTest report saved to: {filename}")
    return filename

def reset_output_urls(output_dir="output/test_urls", confirm=True):
    """Reset the output URLs directory."""
    full_path = os.path.join(project_root, output_dir)
    
    try:
        if confirm:
            print(f"{Fore.RED}WARNING: This will delete all collected URLs in {full_path}{Style.RESET_ALL}")
            user_confirm = input(f"{Fore.YELLOW}Are you sure? (y/n): {Style.RESET_ALL}")
            if user_confirm.lower() != 'y':
                logger.info("Reset canceled by user")
                return False
        
        logger.info(f"Clearing JSON files in directory: {full_path}")
        
        # Create directory if it doesn't exist
        os.makedirs(full_path, exist_ok=True)
        
        # For each JSON file, simply overwrite with empty list
        json_files_cleared = 0
        for file in os.listdir(full_path):
            if file.endswith('.json'):
                file_path = os.path.join(full_path, file)
                try:
                    # Just write an empty list to the file
                    with open(file_path, 'w', encoding='utf-8') as f:
                        json.dump([], f)
                    logger.info(f"Cleared content in: {file_path}")
                    json_files_cleared += 1
                except Exception as e:
                    logger.error(f"Error clearing file {file_path}: {e}")
        
        # Create temp directory if it doesn't exist
        temp_dir = os.path.join(full_path, "temp")
        os.makedirs(temp_dir, exist_ok=True)
        
        if json_files_cleared > 0:
            print(f"{Fore.GREEN}✅ Cleared content in {json_files_cleared} JSON files{Style.RESET_ALL}")
        else:
            print(f"{Fore.YELLOW}No JSON files found to clear{Style.RESET_ALL}")
        
        logger.info(f"Output directory reset successful")
        return True
    except Exception as e:
        logger.error(f"Error resetting output directory: {e}")
        print(f"{Fore.RED}❌ Failed to reset directory: {str(e)}{Style.RESET_ALL}")
        return False

def get_available_crawlers():
    """Get list of available crawler modules."""
    crawler_dir = os.path.join(project_root, "src", "crawlers", "Urls_Crawler")
    crawlers = []
    for file in os.listdir(crawler_dir):
        if file.endswith("_crawler.py"):
            crawler_name = file.replace("_crawler.py", "").lower()
            crawlers.append(crawler_name)
    return sorted(crawlers)

def get_available_categories():
    """Get list of available categories."""
    categories = set()
    
    # Combine categories from all crawlers
    crawlers = get_available_crawlers()
    for crawler in crawlers:
        categories.update(get_site_categories(crawler))
        
    return sorted(categories)

def run_crawl_urls_test() -> TestResult:
    """Test the crawl_urls function."""
    result = TestResult("crawl_urls function test")
    
    try:
        # Assuming crawl_urls is imported from Data_Collection_CLI
        from Data_Collection_CLI import crawl_urls
        
        # Test with a specific category
        categories = ["sport"]
        success = crawl_urls(categories=categories, resume=False)
        
        if success:
            result.set_success("crawl_urls function executed successfully")
        else:
            result.set_failure(Exception("crawl_urls function failed"), "crawl_urls function did not complete successfully")
        
        return result
    except Exception as e:
        return result.set_failure(e, "Exception occurred during crawl_urls test")

def main():
    """Main test function."""
    # Parse arguments
    parser = argparse.ArgumentParser(description="Run crawler tests")
    parser.add_argument("--crawler", help="Specific crawler to test")
    parser.add_argument("--category", help="Specific category to test")
    parser.add_argument("--output-dir", default="output/test_urls", help="Directory to save URLs")
    parser.add_argument("--reset", action="store_true", help="Reset output directory before testing")
    parser.add_argument("--full", action="store_true", help="Run full test checklist on all crawlers and categories")
    parser.add_argument("--test-master", action="store_true", help="Test only the master controller")
    parser.add_argument("--report", action="store_true", help="Generate test report")
    parser.add_argument("--parallel", action="store_true", help="Run tests in parallel")
    parser.add_argument("--workers", type=int, default=2, help="Number of worker threads for parallel testing")
    parser.add_argument("--no-confirm", action="store_true", help="Skip confirmation prompts")
    parser.add_argument("--test-crawl-urls", action="store_true", help="Test crawl_urls function")
    
    args = parser.parse_args()
    
    # Reset output directory if requested
    if args.reset:
        reset_output_urls(args.output_dir, confirm=not args.no_confirm)
    
    results = {}
    
    # Testing options
    if args.test_crawl_urls:
        results = {"crawl_urls": [run_crawl_urls_test()]}
    elif args.test_master:
        results = {"master_controller": [run_master_controller_test()]}
    elif args.full:
        # Run full test checklist
        results = run_full_checklist(parallel=args.parallel, max_workers=args.workers)
    else:
        # Test specific crawler and category
        if args.crawler and args.category:
            results = {f"{args.crawler}_{args.category}": run_checklist_for_crawler(args.crawler, args.category, args.output_dir)}
        else:
            # No specific test selected, show usage
            parser.print_help()
            return
    
    # Print summary
    total_tests = sum(len(tests) for tests in results.values())
    passed_tests = sum(sum(1 for test in tests if test.success) for tests in results.values())
    failed_tests = total_tests - passed_tests
    
    print("\n" + "=" * 80)
    print(f"{Fore.CYAN}TEST EXECUTION SUMMARY{Style.RESET_ALL}")
    print("=" * 80 + "\n")
    
    print(f"Total tests executed: {total_tests}")
    print(f"Passed tests: {passed_tests}")
    print(f"Failed tests: {failed_tests}")
    
    # Generate report if requested
    if args.report:
        report = generate_test_report(results)
        report_path = save_test_report(report)
        print(f"Detailed report saved to: {report_path}")

if __name__ == "__main__":
    main()
