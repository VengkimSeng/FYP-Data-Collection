#!/usr/bin/env python3
"""Test the Post Khmer scraper module."""

import unittest
from unittest.mock import patch, MagicMock
from colorama import Fore, Style

from src.tests.extractor.test_base import BaseExtractorTest

class PostKhmerScraperTests(BaseExtractorTest):
    """Test class for Post Khmer scraper functionality."""
    
    @patch('src.extractors.scrapers.generic_scraper.generic_scrape')
    def test_postkhmer_scraper(self, mock_generic_scrape):
        """Test the Post Khmer scraper."""
        print(f"\n{Fore.CYAN}Testing Post Khmer scraper...{Style.RESET_ALL}")
        
        # Set up expected return value from generic_scrape
        mock_generic_scrape.return_value = {
            "title": "Test Post Khmer Article",
            "content": "Post Khmer Content Test",
            "url": "https://www.postkhmer.com/article/123",
            "category": "test_category"
        }
        
        # Import and test the Post Khmer scraper
        from src.extractors.scrapers.postkhmer_scraper import scrape_postkhmer
        
        # Call the scraper
        test_url = "https://www.postkhmer.com/article/123"
        result = scrape_postkhmer(test_url, "test_category")
        
        # Verify the scraper called generic_scrape with the correct parameters
        mock_generic_scrape.assert_called_once_with(
            test_url, 
            "test_category", 
            "div.section-article-header h2", 
            "article-text"
        )
        
        # Verify the result
        self.assertEqual(result["title"], "Test Post Khmer Article")
        self.assertEqual(result["content"], "Post Khmer Content Test")
        self.assertEqual(result["url"], test_url)
        self.assertEqual(result["category"], "test_category")
        
        print(f"{Fore.GREEN}✓ Post Khmer scraper successfully processed URL{Style.RESET_ALL}")
    
    def test_scraper_registration(self):
        """Test that the Post Khmer scraper is correctly registered in SCRAPER_MAP."""
        print(f"\n{Fore.CYAN}Testing Post Khmer scraper registration...{Style.RESET_ALL}")
        
        from src.extractors.config import SCRAPER_MAP
        from src.extractors.scrapers.postkhmer_scraper import scrape_postkhmer
        
        # Check that the scraper is registered with the correct URL
        self.assertIn("https://www.postkhmer.com", SCRAPER_MAP)
        self.assertEqual(SCRAPER_MAP["https://www.postkhmer.com"], scrape_postkhmer)
        
        print(f"{Fore.GREEN}✓ Post Khmer scraper correctly registered in SCRAPER_MAP{Style.RESET_ALL}")

if __name__ == "__main__":
    unittest.main()
