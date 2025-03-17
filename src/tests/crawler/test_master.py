import time
import os
from colorama import Fore, Style
from src.tests.crawler.test_utils import import_master_controller, TestResult, project_root, logger

def run_master_controller_test() -> TestResult:
    """Test if master controller can be imported and initialized."""
    result = TestResult("Master controller test")
    
    try:
        logger.info("Testing master controller:")
        print(f"\n{Fore.CYAN}Testing Master Controller{Style.RESET_ALL}")
        
        # Step 1: Import master controller
        logger.info("  • Step 1: Importing master controller module")
        print(f"  {Fore.YELLOW}• Step 1: Importing master controller module{Style.RESET_ALL}")
        start_time = time.time()
        module, module_path = import_master_controller()
        
        if not module:
            error_msg = "Failed to import master controller module"
            logger.error(f"  • {error_msg}")
            print(f"    {Fore.RED}❌ {error_msg}{Style.RESET_ALL}")
            return result.set_failure(Exception(error_msg), error_msg)
        
        logger.info("  • Master controller module imported successfully")
        print(f"    {Fore.GREEN}✅ Master controller module imported successfully{Style.RESET_ALL}")
        result.module_path = module_path
        
        # Step 2: Create test output directory
        logger.info("  • Step 2: Creating test output directories")
        print(f"  {Fore.YELLOW}• Step 2: Creating test output directories{Style.RESET_ALL}")
        output_dir = os.path.join(project_root, "output", "test_urls")
        log_dir = os.path.join(project_root, "output", "logs")
        os.makedirs(output_dir, exist_ok=True)
        os.makedirs(log_dir, exist_ok=True)
        print(f"    {Fore.GREEN}✅ Test directories created{Style.RESET_ALL}")
        
        # Step 3: Initialize the controller
        logger.info("  • Step 3: Initializing CrawlerManager")
        print(f"  {Fore.YELLOW}• Step 3: Initializing CrawlerManager{Style.RESET_ALL}")
        try:
            controller = module.CrawlerManager(
                output_dir=output_dir,
                log_dir=log_dir,
                max_workers=1
            )
            
            # Step 4: Check crawler discovery
            logger.info("  • Step 4: Checking crawler discovery")
            print(f"  {Fore.YELLOW}• Step 4: Checking crawler discovery{Style.RESET_ALL}")
            if controller.crawler_names and len(controller.crawler_names) > 0:
                logger.info(f"  • Found {len(controller.crawler_names)} crawlers")
                print(f"    {Fore.GREEN}✅ Found {len(controller.crawler_names)} crawlers{Style.RESET_ALL}")
                for crawler in controller.crawler_names:
                    logger.info(f"    - {crawler}")
                    print(f"      - {crawler}")
                result.set_success(f"Successfully initialized controller with {len(controller.crawler_names)} crawlers")
                result.data['crawlers_found'] = controller.crawler_names
            else:
                error_msg = "Master controller didn't discover any crawlers"
                logger.error(f"  • {error_msg}")
                print(f"    {Fore.RED}❌ {error_msg}{Style.RESET_ALL}")
                result.set_failure(Exception(error_msg), error_msg)
        except Exception as e:
            logger.error(f"  • Failed to initialize CrawlerManager: {e}")
            print(f"    {Fore.RED}❌ Failed to initialize CrawlerManager: {e}{Style.RESET_ALL}")
            result.set_failure(e, "Failed to initialize CrawlerManager")
            
        result.duration = time.time() - start_time
        return result
    except Exception as e:
        logger.error(f"  • Unexpected error in master controller test: {e}")
        print(f"    {Fore.RED}❌ Unexpected error in master controller test: {e}{Style.RESET_ALL}")
        return result.set_failure(e)
