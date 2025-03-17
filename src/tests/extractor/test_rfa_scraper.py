#!/usr/bin/env python3
"""Test the RFA scraper module."""

import unittest
from unittest.mock import patch, MagicMock, call
from colorama import Fore, Style

from src.tests.extractor.test_base import BaseExtractorTest

class RfaScraperTests(BaseExtractorTest):
    """Test class for RFA scraper functionality."""
    
    @patch('src.extractors.scrapers.generic_scraper.WebDriverWait')
    @patch('src.extractors.browser.create_driver')
    def test_rfa_scraper(self, mock_create_driver, mock_wait):
        """Test basic functionality of RFA scraper."""
        print(f"\n{Fore.CYAN}Testing RFA scraper...{Style.RESET_ALL}")
        
        # Set up the driver mock
        mock_driver = MagicMock()
        mock_create_driver.return_value = mock_driver
        
        # Set up for WebDriverWait
        mock_wait_instance = MagicMock()
        mock_wait.return_value = mock_wait_instance
        
        # Set up title and content elements
        mock_title = MagicMock()
        mock_title.text = "Test RFA Article"
        
        mock_content = MagicMock()
        mock_paragraphs = [MagicMock(), MagicMock()]
        mock_paragraphs[0].text = "RFA Paragraph 1"
        mock_paragraphs[1].text = "RFA Paragraph 2"
        mock_content.find_elements.return_value = mock_paragraphs
        
        # Configure wait to return our mocks
        mock_wait_instance.until.side_effect = [mock_title, mock_content]
        
        # Call the extract function
        from src.extractors.scrapers import rfa_scraper
        result = rfa_scraper.extract_article("https://www.rfa.org/english/news/12345.html", "politic")
        
        # Verify the result
        self.assertIsNotNone(result)
        self.assertEqual(result["title"], "Test RFA Article")
        self.assertEqual(result["content"], "RFA Paragraph 1\nRFA Paragraph 2")
        self.assertEqual(result["category"], "politic")
        
        # Verify WebDriverWait was called correctly
        mock_wait.assert_any_call(mock_driver, 30)
        
        print(f"{Fore.GREEN}✓ RFA scraper successfully processed URL{Style.RESET_ALL}")
    
    def test_scraper_registration(self):
        """Test that the RFA scraper is correctly registered in SCRAPER_MAP."""
        print(f"\n{Fore.CYAN}Testing RFA scraper registration...{Style.RESET_ALL}")
        
        from src.extractors.config import SCRAPER_MAP
        from src.extractors.scrapers.rfa_scraper import scrape_rfa
        
        # Check that the scraper is registered with the correct URL
        self.assertIn("https://www.rfa.org", SCRAPER_MAP)
        self.assertEqual(SCRAPER_MAP["https://www.rfa.org"], scrape_rfa)
        
        print(f"{Fore.GREEN}✓ RFA scraper correctly registered in SCRAPER_MAP{Style.RESET_ALL}")

if __name__ == "__main__":
    unittest.main()
