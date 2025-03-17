#!/usr/bin/env python3
"""Test the DAP News scraper module."""

import unittest
from unittest.mock import patch, MagicMock
from colorama import Fore, Style

from src.tests.extractor.test_base import BaseExtractorTest

class DapNewsScraperTests(BaseExtractorTest):
    """Test class for DAP News scraper functionality."""
    
    @patch('src.extractors.scrapers.generic_scraper.generic_scrape')
    def test_dapnews_scraper(self, mock_generic_scrape):
        """Test the DAP News scraper."""
        print(f"\n{Fore.CYAN}Testing DAP News scraper...{Style.RESET_ALL}")
        
        # Set up expected return value from generic_scrape
        mock_generic_scrape.return_value = {
            "title": "Test DAP News Article",
            "content": "DAP News Content Test",
            "url": "https://dap-news.com/article/123",
            "category": "test_category"
        }
        
        # Import and test the DAP News scraper
        from src.extractors.scrapers.dapnews_scraper import scrape_dapnews
        
        # Call the scraper
        test_url = "https://dap-news.com/article/123"
        result = scrape_dapnews(test_url, "test_category")
        
        # Verify the scraper called generic_scrape with the correct parameters
        mock_generic_scrape.assert_called_once_with(
            test_url, 
            "test_category", 
            "title", 
            "content-main", 
            is_id=True
        )
        
        # Verify the result
        self.assertEqual(result["title"], "Test DAP News Article")
        self.assertEqual(result["content"], "DAP News Content Test")
        self.assertEqual(result["url"], test_url)
        self.assertEqual(result["category"], "test_category")
        
        print(f"{Fore.GREEN}✓ DAP News scraper successfully processed URL{Style.RESET_ALL}")
    
    def test_scraper_registration(self):
        """Test that the DAP News scraper is correctly registered in SCRAPER_MAP."""
        print(f"\n{Fore.CYAN}Testing DAP News scraper registration...{Style.RESET_ALL}")
        
        from src.extractors.config import SCRAPER_MAP
        from src.extractors.scrapers.dapnews_scraper import scrape_dapnews
        
        # Check that the scraper is registered with the correct URL
        self.assertIn("https://dap-news.com", SCRAPER_MAP)
        self.assertEqual(SCRAPER_MAP["https://dap-news.com"], scrape_dapnews)
        
        print(f"{Fore.GREEN}✓ DAP News scraper correctly registered in SCRAPER_MAP{Style.RESET_ALL}")

if __name__ == "__main__":
    unittest.main()
