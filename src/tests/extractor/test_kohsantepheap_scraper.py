#!/usr/bin/env python3
"""Test the Kohsantepheap scraper module."""

import unittest
from unittest.mock import patch, MagicMock
from colorama import Fore, Style

from src.tests.extractor.test_base import BaseExtractorTest

class KohsantepheapScraperTests(BaseExtractorTest):
    """Test class for Kohsantepheap scraper functionality."""
    
    @patch('src.extractors.scrapers.generic_scraper.generic_scrape')
    def test_kohsantepheap_scraper(self, mock_generic_scrape):
        """Test the Kohsantepheap scraper."""
        print(f"\n{Fore.CYAN}Testing Kohsantepheap scraper...{Style.RESET_ALL}")
        
        # Set up expected return value from generic_scrape
        mock_generic_scrape.return_value = {
            "title": "Test Kohsantepheap Article",
            "content": "Kohsantepheap Content Test",
            "url": "https://kohsantepheapdaily.com.kh/article/123",
            "category": "test_category"
        }
        
        # Import and test the Kohsantepheap scraper
        from src.extractors.scrapers.kohsantepheap_scraper import scrape_kohsantepheap
        
        # Call the scraper
        test_url = "https://kohsantepheapdaily.com.kh/article/123"
        result = scrape_kohsantepheap(test_url, "test_category")
        
        # Verify the scraper called generic_scrape with the correct parameters
        mock_generic_scrape.assert_called_once_with(
            test_url, 
            "test_category", 
            "div.article-recap h1", 
            "content-text"
        )
        
        # Verify the result
        self.assertEqual(result["title"], "Test Kohsantepheap Article")
        self.assertEqual(result["content"], "Kohsantepheap Content Test")
        self.assertEqual(result["url"], test_url)
        self.assertEqual(result["category"], "test_category")
        
        print(f"{Fore.GREEN}✓ Kohsantepheap scraper successfully processed URL{Style.RESET_ALL}")
    
    def test_scraper_registration(self):
        """Test that the Kohsantepheap scraper is correctly registered in SCRAPER_MAP."""
        print(f"\n{Fore.CYAN}Testing Kohsantepheap scraper registration...{Style.RESET_ALL}")
        
        from src.extractors.config import SCRAPER_MAP
        from src.extractors.scrapers.kohsantepheap_scraper import scrape_kohsantepheap
        
        # Check that the scraper is registered with the correct URL
        self.assertIn("https://kohsantepheapdaily.com.kh", SCRAPER_MAP)
        self.assertEqual(SCRAPER_MAP["https://kohsantepheapdaily.com.kh"], scrape_kohsantepheap)
        
        print(f"{Fore.GREEN}✓ Kohsantepheap scraper correctly registered in SCRAPER_MAP{Style.RESET_ALL}")

if __name__ == "__main__":
    unittest.main()
