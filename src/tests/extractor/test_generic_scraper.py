#!/usr/bin/env python3
"""Test the generic scraper module."""

import unittest
from unittest.mock import patch, MagicMock
from colorama import Fore, Style

from src.extractors.scrapers.generic_scraper import generic_scrape

class GenericScraperTests(unittest.TestCase):
    """Test cases for the generic scraper."""
    
    @patch('src.extractors.scrapers.generic_scraper.create_driver')
    @patch('src.extractors.scrapers.generic_scraper.extract_title')
    @patch('src.extractors.scrapers.generic_scraper.extract_content')
    def test_generic_scraper(self, mock_extract_content, mock_extract_title, mock_create_driver):
        """Test basic functionality of generic scraper."""
        # Set up mocks
        mock_driver = MagicMock()
        mock_create_driver.return_value = mock_driver
        
        mock_extract_title.return_value = "Test Article Title"
        mock_extract_content.return_value = "Test article content paragraph."
        
        with patch('src.extractors.scrapers.generic_scraper.is_scraped', return_value=False):
            # Test extraction function
            result = generic_scrape("https://example.com/article", "test_category")
            
            # Verify result
            self.assertIsNotNone(result)
            self.assertEqual(result["title"], "Test Article Title")
            self.assertEqual(result["content"], "Test article content paragraph.")
            self.assertEqual(result["category"], "test_category")
            self.assertEqual(result["url"], "https://example.com/article")
            
            # Verify driver was used correctly
            mock_create_driver.assert_called_once()
            mock_driver.get.assert_called_once_with("https://example.com/article")
            mock_extract_title.assert_called_once_with(mock_driver)
            mock_extract_content.assert_called_once_with(mock_driver)

if __name__ == "__main__":
    unittest.main()
