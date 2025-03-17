#!/usr/bin/env python3
"""Test the BTV scraper module."""

import unittest
from unittest.mock import patch, MagicMock
from colorama import Fore, Style

from src.tests.extractor.test_base import BaseExtractorTest

class BtvScraperTests(BaseExtractorTest):
    """Test class for BTV scraper functionality."""
    
    @patch('src.extractors.scrapers.generic_scraper.generic_scrape')
    def test_btv_scraper(self, mock_generic_scrape):
        """Test the BTV scraper."""
        print(f"\n{Fore.CYAN}Testing BTV scraper...{Style.RESET_ALL}")
        
        # Set up expected return value from generic_scrape
        mock_generic_scrape.return_value = {
            "title": "Test BTV Article",
            "content": "BTV Content Test",
            "url": "https://btv.com.kh/article/123",
            "category": "test_category"
        }
        
        # Import and test the BTV scraper
        from src.extractors.scrapers.btv_scraper import scrape_btv
        
        # Call the scraper
        test_url = "https://btv.com.kh/article/123"
        result = scrape_btv(test_url, "test_category")
        
        # Verify the scraper called generic_scrape with the correct parameters
        mock_generic_scrape.assert_called_once_with(test_url, "test_category", "h4.color", "font-size-detail.textview")
        
        # Verify the result
        self.assertEqual(result["title"], "Test BTV Article")
        self.assertEqual(result["content"], "BTV Content Test")
        self.assertEqual(result["url"], test_url)
        self.assertEqual(result["category"], "test_category")
        
        print(f"{Fore.GREEN}✓ BTV scraper successfully processed URL{Style.RESET_ALL}")
    
    def test_scraper_registration(self):
        """Test that the BTV scraper is correctly registered in SCRAPER_MAP."""
        print(f"\n{Fore.CYAN}Testing BTV scraper registration...{Style.RESET_ALL}")
        
        from src.extractors.config import SCRAPER_MAP
        from src.extractors.scrapers.btv_scraper import scrape_btv
        
        # Check that the scraper is registered with the correct URL
        self.assertIn("https://btv.com.kh", SCRAPER_MAP)
        self.assertEqual(SCRAPER_MAP["https://btv.com.kh"], scrape_btv)
        
        print(f"{Fore.GREEN}✓ BTV scraper correctly registered in SCRAPER_MAP{Style.RESET_ALL}")

if __name__ == "__main__":
    unittest.main()
