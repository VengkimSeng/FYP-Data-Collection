#!/usr/bin/env python3
"""Tests for the browser module."""

import unittest
from unittest.mock import patch, MagicMock

from src.extractors import browser

class BrowserTests(unittest.TestCase):
    """Test cases for browser module."""
    
    def test_get_chrome_options(self):
        """Test that chrome options are created correctly."""
        # Test with default parameters
        options = browser.get_chrome_options()
        self.assertIsNotNone(options)
        
        # Test with non-default parameters (headless=False, no_images=False)
        options = browser.get_chrome_options(headless=False, no_images=False)
        self.assertIsNotNone(options)
    
    @patch('src.extractors.browser.webdriver.Chrome')
    @patch('src.extractors.browser.Service')
    @patch('src.extractors.browser.ChromeDriverManager')
    def test_create_driver(self, mock_manager, mock_service, mock_driver):
        """Test driver creation."""
        # Set up mocks
        mock_manager.return_value.install.return_value = '/path/to/chromedriver'
        mock_service.return_value = 'service'
        mock_driver.return_value = MagicMock()
        
        # Test with default parameters
        driver = browser.create_driver()
        self.assertIsNotNone(driver)
        mock_driver.assert_called_once()
        
        # Reset mocks
        mock_driver.reset_mock()
        mock_service.reset_mock()
        mock_manager.reset_mock()
        
        # Test with non-default parameters (headless=False, no_images=False)
        driver = browser.create_driver(headless=False, no_images=False)
        self.assertIsNotNone(driver)
        mock_driver.assert_called_once()
    
    def test_close_driver(self):
        """Test driver closing."""
        # Create a mock driver
        mock_driver = MagicMock()
        
        # Test closing
        browser.close_driver(mock_driver)
        mock_driver.quit.assert_called_once()
        
        # Test closing None (should not raise error)
        browser.close_driver(None)

if __name__ == "__main__":
    unittest.main()
