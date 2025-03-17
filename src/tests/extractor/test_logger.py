#!/usr/bin/env python3
"""Test the logger module."""

import os
import sys
import unittest
from unittest.mock import patch, MagicMock
from colorama import Fore, Style

class LoggerTests(unittest.TestCase):
    """Test class for logger functionality."""
    
    def setUp(self):
        """Set up test environment."""
        # Patch print function
        self.print_patcher = patch('builtins.print')
        self.mock_print = self.print_patcher.start()
        
        # Patch logger
        self.logger_patcher = patch('src.extractors.logger.logger')
        self.mock_logger = self.logger_patcher.start()
    
    def tearDown(self):
        """Tear down test environment."""
        self.print_patcher.stop()
        self.logger_patcher.stop()
    
    def test_log_scrape_status(self):
        """Test the log_scrape_status function."""
        print(f"\n{Fore.CYAN}Testing log_scrape_status function...{Style.RESET_ALL}")
        
        from src.extractors.logger import log_scrape_status
        
        # Test with plain message
        log_scrape_status("Test message")
        self.mock_print.assert_called_with("Test message")
        self.mock_logger.info.assert_called_with("Test message")
        
        # Test with colored message
        colored_message = f"{Fore.GREEN}Success{Style.RESET_ALL}"
        log_scrape_status(colored_message)
        self.mock_print.assert_called_with(colored_message)
        self.mock_logger.info.assert_called_with("Success")  # Color codes should be stripped
        
        print(f"{Fore.GREEN}✓ log_scrape_status correctly logs messages{Style.RESET_ALL}")
    
    def test_log_error(self):
        """Test the log_error function."""
        print(f"\n{Fore.CYAN}Testing log_error function...{Style.RESET_ALL}")
        
        from src.extractors.logger import log_error
        
        # Test with message only
        log_error("Test error")
        self.mock_logger.error.assert_called_with("Test error")
        
        # Test with exception
        test_exception = Exception("Test exception")
        log_error("Error occurred", test_exception)
        self.mock_logger.error.assert_called_with("Error occurred: Test exception", exc_info=True)
        
        print(f"{Fore.GREEN}✓ log_error correctly logs errors{Style.RESET_ALL}")
    
    def test_log_debug(self):
        """Test the log_debug function."""
        print(f"\n{Fore.CYAN}Testing log_debug function...{Style.RESET_ALL}")
        
        from src.extractors.logger import log_debug
        
        # Test debug logging
        log_debug("Debug message")
        self.mock_logger.debug.assert_called_with("Debug message")
        
        print(f"{Fore.GREEN}✓ log_debug correctly logs debug messages{Style.RESET_ALL}")

if __name__ == "__main__":
    unittest.main()
