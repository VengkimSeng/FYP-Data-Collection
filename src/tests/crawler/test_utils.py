import os
import sys
import time
import traceback
import json
import importlib.util
from typing import Dict, Set, List, Tuple
from colorama import Fore, Style

# Add project root to path for imports
project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
sys.path.append(project_root)

from src.utils.log_utils import setup_logger

# Initialize logger
log_path = os.path.join(project_root, "output", "logs", "tests", "test_crawler.log")
logger = setup_logger('test_crawler', log_path)

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
