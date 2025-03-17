#!/usr/bin/env python3
"""Test the Sabay scraper module."""

import unittest
from unittest.mock import patch, MagicMock, ANY
from colorama import Fore, Style

from src.tests.extractor.test_base import BaseExtractorTest

class SabayScraperTests(BaseExtractorTest):
    """Test class for Sabay scraper functionality."""
    
    @patch('src.extractors.scrapers.sabay_scraper.create_driver')
    @patch('src.extractors.scrapers.sabay_scraper.WebDriverWait')
    @patch('src.extractors.scrapers.sabay_scraper.save_article_data')
    def test_sabay_scraper(self, mock_save_article_data, mock_wait, mock_create_driver):
        """Test the Sabay scraper."""
        print(f"\n{Fore.CYAN}Testing Sabay scraper...{Style.RESET_ALL}")
        
        # Set up mock driver and elements
        mock_driver = MagicMock()
        mock_create_driver.return_value = mock_driver
        
        # Set up mock elements
        mock_title_element = MagicMock()
        mock_title_element.text = "Test Sabay Article"
        
        mock_content_div = MagicMock()
        mock_p_elements = [MagicMock(), MagicMock()]
        mock_p_elements[0].text = "Paragraph 1"
        mock_p_elements[1].text = "Paragraph 2"
        mock_p_elements[0].get_attribute.return_value = ""  # Not an ad
        mock_p_elements[1].get_attribute.return_value = ""  # Not an ad
        mock_content_div.find_elements.return_value = mock_p_elements
        
        # Set up WebDriverWait mock
        mock_wait_instance = MagicMock()
        mock_wait_instance.until.side_effect = [mock_title_element, mock_content_div]
        mock_wait.return_value = mock_wait_instance
        
        # Import and test the Sabay scraper
        from src.extractors.scrapers.sabay_scraper import scrape_sabay
        
        # Mock is_scraped to return False
        with patch('src.extractors.scrapers.sabay_scraper.is_scraped', return_value=False):
            # Call the scraper
            test_url = "https://news.sabay.com.kh/article/123"
            result = scrape_sabay(test_url, "test_category")
            
            # Verify the driver was created and used correctly
            mock_create_driver.assert_called_once()
            mock_driver.get.assert_called_once_with(test_url)
            
            # Verify WebDriverWait was called correctly - use ANY for the function comparison
            mock_wait.assert_any_call(mock_driver, 30)
            
            # Verify result was saved
            mock_save_article_data.assert_called_once()
            
            # Verify the result contains expected data
            self.assertEqual(result["title"], "Test Sabay Article")
            self.assertEqual(result["content"], "Paragraph 1\nParagraph 2")
            self.assertEqual(result["url"], test_url)
            self.assertEqual(result["category"], "test_category")
            
            # Verify driver was quit
            mock_driver.quit.assert_called_once()
        
        print(f"{Fore.GREEN}✓ Sabay scraper successfully processed URL{Style.RESET_ALL}")
    
    def test_scraper_registration(self):
        """Test that the Sabay scraper is correctly registered in SCRAPER_MAP."""
        print(f"\n{Fore.CYAN}Testing Sabay scraper registration...{Style.RESET_ALL}")
        
        from src.extractors.config import SCRAPER_MAP
        
        # Check that the scraper is registered with the correct URL
        self.assertIn("news.sabay.com.kh", SCRAPER_MAP)
        self.assertEqual(SCRAPER_MAP["news.sabay.com.kh"], "sabay_scraper")
        
        print(f"{Fore.GREEN}✓ Sabay scraper correctly registered in SCRAPER_MAP{Style.RESET_ALL}")

if __name__ == "__main__":
    unittest.main()
