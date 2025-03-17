import os
import sys
import argparse
from colorama import Fore, Style, init

# Initialize colorama
init(autoreset=True)

# Add project root to path for imports
project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
sys.path.append(project_root)

# Add src directory to path for imports
src_path = os.path.join(project_root, 'src')
sys.path.append(src_path)

# Now import from the project with the correct path
from src.tests.test_crawler import (
    run_checklist_for_crawler,
    run_module_import_test,
    run_function_existence_test,
    run_source_urls_test,
    run_crawl_minimal_test,
    run_save_test,
    run_filter_urls_test,
    run_master_controller_test,
    run_crawl_urls_test,
    generate_test_report,
    save_test_report,
    reset_output_urls,
    get_available_crawlers,
    get_available_categories,
    get_site_categories,
    run_full_checklist,
    TestResult,
    logger
)

def import_master_controller():
    """Import the master controller module."""
    try:
        import src.crawlers.master_crawler_controller as master_controller
        return master_controller, master_controller.__file__
    except ImportError as e:
        logger.error(f"Failed to import master controller: {e}")
        return None, None

def main():
    """Main test function."""
    # Parse arguments
    parser = argparse.ArgumentParser(description="Run crawler tests")
    parser.add_argument("--crawler", help="Specific crawler to test")
    parser.add_argument("--category", help="Specific category to test")
    parser.add_argument("--crawlers", nargs="+", help="List of crawlers to test")
    parser.add_argument("--categories", nargs="+", help="List of categories to test")
    parser.add_argument("--output-dir", default="output/test_urls", help="Directory to save URLs")
    parser.add_argument("--reset", action="store_true", help="Reset output directory before testing")
    parser.add_argument("--full", action="store_true", help="Run full test checklist on all crawlers and categories")
    parser.add_argument("--report", action="store_true", help="Generate test report")
    parser.add_argument("--parallel", action="store_true", help="Run tests in parallel")
    parser.add_argument("--workers", type=int, default=2, help="Number of worker threads for parallel testing")
    parser.add_argument("--no-confirm", action="store_true", help="Skip confirmation prompts")
    parser.add_argument("--quick", action="store_true", help="Run only quick tests (module imports and function checks)")
    parser.add_argument("--test-master", action="store_true", help="Test only the master controller")
    
    # Add individual test options
    parser.add_argument("--test-import", action="store_true", help="Run only module import test")
    parser.add_argument("--test-functions", action="store_true", help="Run only function existence test")
    parser.add_argument("--test-sources", action="store_true", help="Run only source URLs test")
    parser.add_argument("--test-filtering", action="store_true", help="Run only URL filtering test")
    parser.add_argument("--test-crawl", action="store_true", help="Run only minimal crawl test")
    parser.add_argument("--test-saving", action="store_true", help="Run only URL saving test")
    parser.add_argument("--test-master-import", action="store_true", help="Test only master controller module import")
    parser.add_argument("--test-master-init", action="store_true", help="Test only master controller initialization")
    parser.add_argument("--test-master-discovery", action="store_true", help="Test only master controller crawler discovery")
    parser.add_argument("--test-crawl-urls", action="store_true", help="Test crawl_urls function")
    
    args = parser.parse_args()
    
    # Create output directory if it doesn't exist
    output_dir = os.path.join(project_root, args.output_dir)
    os.makedirs(output_dir, exist_ok=True)
    
    # Print the test checklist at the beginning
    print("\n" + "=" * 80)
    print(f"{Fore.CYAN}CRAWLER TEST CHECKLIST{Style.RESET_ALL}")
    print("=" * 80)
    print("\nThe following tests will be performed:")
    print(f"  1. {Fore.GREEN}Module Import Test{Style.RESET_ALL} - Verifies crawler modules can be imported")
    print(f"  2. {Fore.GREEN}Function Existence Test{Style.RESET_ALL} - Checks required functions and signatures")
    print(f"  3. {Fore.GREEN}Source URLs Test{Style.RESET_ALL} - Validates source URLs for each category")
    print(f"  4. {Fore.GREEN}URL Filtering Test{Style.RESET_ALL} - Tests URL filtering functionality")
    print(f"  5. {Fore.GREEN}Minimal Crawl Test{Style.RESET_ALL} - Performs a small crawl to validate functionality")
    print(f"  6. {Fore.GREEN}URL Saving Test{Style.RESET_ALL} - Checks if URLs can be saved correctly")
    print("\nMaster Controller Tests:")
    print(f"  1. {Fore.GREEN}Module Import{Style.RESET_ALL} - Can import controller module")
    print(f"  2. {Fore.GREEN}Initialization{Style.RESET_ALL} - Can create controller instance")
    print(f"  3. {Fore.GREEN}Crawler Discovery{Style.RESET_ALL} - Controller finds available crawlers")
    print("=" * 80 + "\n")
    
    # Add confirmation only for full tests which might take a long time
    if args.full and not args.no_confirm:
        confirm = input("Press Enter to begin testing, or Ctrl+C to cancel...")
    
    # Reset output directory if requested
    if args.reset:
        if reset_output_urls(args.output_dir, confirm=not args.no_confirm):
            logger.info("Output directory reset successful")
        else:
            logger.warning("Output directory reset failed or was canceled")
    
    # Determine what to test
    crawlers = []
    if args.crawler:
        crawlers = [args.crawler]
    elif args.crawlers:
        crawlers = args.crawlers
    else:
        crawlers = get_available_crawlers()
        print(f"{Fore.CYAN}Found {len(crawlers)} available crawlers: {', '.join(crawlers)}{Style.RESET_ALL}")
    
    categories = []
    if args.category:
        categories = [args.category]
    elif args.categories:
        categories = args.categories
        
    results = {}
    
    # Individual test handling - Crawler-specific tests
    if any([args.test_import, args.test_functions, args.test_sources, 
            args.test_filtering, args.test_crawl, args.test_saving]):
        
        if not args.crawler and not args.crawlers:
            print(f"{Fore.YELLOW}Warning: No crawler specified, using all available crawlers{Style.RESET_ALL}")
        
        for crawler in crawlers:
            # For tests that need category
            crawler_categories = categories if categories else get_site_categories(crawler)
            if not crawler_categories and (args.test_sources or args.test_crawl or args.test_saving):
                print(f"{Fore.YELLOW}Warning: No categories specified for {crawler}, using first available category{Style.RESET_ALL}")
                crawler_categories = get_site_categories(crawler)[:1]
                
            results[crawler] = []
                
            # Run individual tests
            if args.test_import:
                print(f"\nRunning Module Import Test for {crawler}...")
                results[crawler].append(run_module_import_test(crawler))
                
            if args.test_functions:
                print(f"\nRunning Function Existence Test for {crawler}...")
                results[crawler].append(run_function_existence_test(crawler))
                
            if args.test_filtering:
                print(f"\nRunning URL Filtering Test for {crawler}...")
                results[crawler].append(run_filter_urls_test(crawler))
                
            # Tests that need category
            for category in crawler_categories:
                key = f"{crawler}_{category}"
                results[key] = []
                
                if args.test_sources:
                    print(f"\nRunning Source URLs Test for {crawler} - {category}...")
                    results[key].append(run_source_urls_test(crawler, category))
                    
                if args.test_crawl:
                    print(f"\nRunning Minimal Crawl Test for {crawler} - {category}...")
                    results[key].append(run_crawl_minimal_test(crawler, category))
                    
                if args.test_saving:
                    print(f"\nRunning URL Saving Test for {crawler} - {category}...")
                    results[key].append(run_save_test(crawler, category, args.output_dir))
    
    # Individual test handling - Master controller tests
    elif args.test_master_import or args.test_master_init or args.test_master_discovery:
        print("\nRunning individual Master Controller tests...")
        results["master_controller"] = []
        
        if args.test_master_import:
            print("Testing Master Controller module import...")
            module, module_path = import_master_controller()
            result = TestResult("Master controller import test")
            if module:
                result.module_path = module_path
                result.set_success("Successfully imported master controller module")
            else:
                result.set_failure(Exception("Failed to import master controller module"))
            results["master_controller"].append(result)
            
        if args.test_master_init:
            print("Testing Master Controller initialization...")
            try:
                # First need to import the module
                module, module_path = import_master_controller()
                if not module:
                    raise Exception("Failed to import master controller module")
                
                # Try initializing the controller
                result = TestResult("Master controller initialization test")
                result.module_path = module_path
                
                # Create test output directory
                output_dir = os.path.join(project_root, "output", "test_urls")
                log_dir = os.path.join(project_root, "output", "logs")
                os.makedirs(output_dir, exist_ok=True)
                os.makedirs(log_dir, exist_ok=True)
                
                controller = module.CrawlerManager(
                    output_dir=output_dir,
                    log_dir=log_dir,
                    max_workers=1
                )
                
                result.set_success("Successfully initialized CrawlerManager")
                results["master_controller"].append(result)
            except Exception as e:
                result = TestResult("Master controller initialization test")
                result.set_failure(e, f"Failed to initialize CrawlerManager: {e}")
                results["master_controller"].append(result)
                
        if args.test_master_discovery:
            print("Testing Master Controller crawler discovery...")
            try:
                # First need to import the module and initialize
                module, module_path = import_master_controller()
                if not module:
                    raise Exception("Failed to import master controller module")
                
                # Create test output directory
                output_dir = os.path.join(project_root, "output", "test_urls")
                log_dir = os.path.join(project_root, "output", "logs")
                os.makedirs(output_dir, exist_ok=True)
                os.makedirs(log_dir, exist_ok=True)
                
                # Try initializing the controller
                controller = module.CrawlerManager(
                    output_dir=output_dir,
                    log_dir=log_dir,
                    max_workers=1
                )
                
                # Test crawler discovery
                result = TestResult("Master controller crawler discovery test")
                result.module_path = module_path
                
                if controller.crawler_names and len(controller.crawler_names) > 0:
                    result.set_success(f"Found {len(controller.crawler_names)} crawlers")
                    result.data['crawlers_found'] = controller.crawler_names
                    print(f"Discovered crawlers: {', '.join(controller.crawler_names)}")
                else:
                    result.set_failure(Exception("No crawlers found"))
                
                results["master_controller"].append(result)
                
            except Exception as e:
                result = TestResult("Master controller crawler discovery test")
                result.set_failure(e, f"Failed to test crawler discovery: {e}")
                results["master_controller"].append(result)
    
    # Special case for testing just the master controller
    elif args.test_master:
        results = {"master_controller": [run_master_controller_test()]}
    # Run tests
    elif args.full:
        # Run full test checklist
        logger.info("Running full test checklist...")
        results = run_full_checklist(
            crawlers, 
            categories, 
            parallel=args.parallel, 
            max_workers=args.workers
        )
    elif args.test_crawl_urls:
        # Test crawl_urls function
        results = {"crawl_urls": [run_crawl_urls_test()]}
    else:
        # Default behavior: run the complete checklist for specified crawlers/categories
        logger.info("Running default test checklist...")
        
        # Initialize results dictionary
        results = {}
        
        # First test the master controller
        print(f"\n{Fore.CYAN}Running master controller test...{Style.RESET_ALL}")
        results["master_controller"] = [run_master_controller_test()]
        
        # Then run tests for each crawler
        if not crawlers:
            print(f"{Fore.YELLOW}Warning: No crawlers specified. Use --crawler or --crawlers to specify crawlers.{Style.RESET_ALL}")
        else:
            for crawler in crawlers:
                print(f"\n{Fore.CYAN}Running tests for crawler: {crawler}{Style.RESET_ALL}")
                crawler_categories = categories if categories else get_site_categories(crawler)
                
                if not crawler_categories:
                    print(f"{Fore.YELLOW}Warning: No categories found for {crawler}. Skipping...{Style.RESET_ALL}")
                    continue
                
                print(f"{Fore.YELLOW}Testing {len(crawler_categories)} categories for {crawler}: {', '.join(crawler_categories)}{Style.RESET_ALL}")
                
                # Run tests for each crawler-category combination
                for category in crawler_categories:
                    key = f"{crawler}_{category}"
                    print(f"\n{Fore.CYAN}Testing {crawler} with category {category}...{Style.RESET_ALL}")
                    results[key] = run_checklist_for_crawler(crawler, category, args.output_dir)
        
    # Print summary with more detailed information
    print("\n" + "=" * 80)
    print(f"{Fore.CYAN}TEST EXECUTION SUMMARY{Style.RESET_ALL}")
    print("=" * 80 + "\n")
    
    total_tests = sum(len(tests) for tests in results.values())
    passed_tests = sum(sum(1 for test in tests if test.success) for tests in results.values())
    failed_tests = total_tests - passed_tests
    
    print(f"{Fore.YELLOW}Total crawlers tested:{Style.RESET_ALL} {len(results) - (1 if 'master_controller' in results else 0)}")
    print(f"{Fore.YELLOW}Total tests executed:{Style.RESET_ALL} {total_tests}")
    print(f"{Fore.GREEN}Passed tests:{Style.RESET_ALL} {passed_tests}")
    print(f"{Fore.RED}Failed tests:{Style.RESET_ALL} {failed_tests}")
    success_rate = 100 * passed_tests / total_tests if total_tests > 0 else 0
    print(f"{Fore.YELLOW}Success rate:{Style.RESET_ALL} {success_rate:.1f}%\n")
    
    # Detailed results by crawler/category
    print(f"{Fore.CYAN}DETAILED RESULTS BY CRAWLER{Style.RESET_ALL}")
    for section, tests in results.items():
        passed = sum(1 for test in tests if test.success)
        total = len(tests)
        success_emoji = "✅" if passed == total else "⚠️" if passed > 0 else "❌"
        
        if section == "master_controller":
            print(f"{success_emoji} Master Controller: {passed}/{total} tests passed")
        else:
            parts = section.split("_")
            crawler = parts[0]
            category = "_".join(parts[1:]) if len(parts) > 1 else "N/A"
            print(f"{success_emoji} {crawler.capitalize()} - {category}: {passed}/{total} tests passed")
    
    # Print detailed results for failed tests
    print("==== Failed Tests ====\n")
    have_failures = False
    
    for section, tests in results.items():
        failed_tests = [test for test in tests if not test.success]
        if failed_tests:
            have_failures = True
            print(f"\n{section}:")
            for test in failed_tests:
                print(f"  ❌ {test.test_name}: {test.message}")
                if test.error_path and test.error_line:
                    print(f"     Error location: {os.path.relpath(test.error_path, project_root)}:{test.error_line}")
                if test.error:
                    print(f"     Error details: {test.error}")
    
    if not have_failures:
        print("All tests passed successfully!")
    
    # Generate report if requested
    if args.report:
        report = generate_test_report(results)
        report_path = save_test_report(report, os.path.join("output", "test_reports"))
        print(f"\nDetailed report saved to: {report_path}")

if __name__ == "__main__":
    main()
