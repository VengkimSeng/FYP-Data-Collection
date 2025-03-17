#!/usr/bin/env python3
"""Test the extractor adapter module."""

import unittest
from unittest.mock import patch, MagicMock
from colorama import Fore, Style

class AdapterTests(unittest.TestCase):
    """Test cases for the extractor adapter."""
    
    def test_adapter_calls_specific_scraper(self):
        """Test that the adapter calls the specific scraper for a known domain."""
        # Mock the scrapers dictionary
        test_scraper = MagicMock()
        scrapers = {"test.com": test_scraper}
        
        with patch('src.extractors.scrapers.extractor_adapter.SCRAPERS', scrapers):
            from src.extractors.scrapers.extractor_adapter import create_extractor_for_domain
            extractor = create_extractor_for_domain("test.com")
            self.assertIsNotNone(extractor)
            
            # Call extract_article and verify it calls our mock scraper
            test_url = "https://test.com/article"
            test_category = "test_category"
            extractor.extract_article(test_url, test_category)
            
            # Verify the correct scraper was called with expected arguments
            test_scraper.assert_called_once_with(test_url, test_category)
    
    def test_adapter_fallback_to_generic(self):
        """Test that the adapter falls back to generic scraper for unknown domains."""
        # Mock an empty scrapers dictionary and the generic_scraper
        scrapers = {}
        mock_generic_scrape = MagicMock()
        
        with patch('src.extractors.scrapers.extractor_adapter.SCRAPERS', scrapers):
            with patch('src.extractors.scrapers.generic_scraper.generic_scrape', mock_generic_scrape):
                from src.extractors.scrapers.extractor_adapter import create_extractor_for_domain
                extractor = create_extractor_for_domain("unknown.com")
                self.assertIsNotNone(extractor)
                
                # Call extract_article and verify it calls the generic scraper
                test_url = "https://unknown.com/article"
                test_category = "test_category"
                extractor.extract_article(test_url, test_category)  # Remove is_id parameter
                
                # Verify the generic scraper was called with expected arguments
                mock_generic_scrape.assert_called_once_with(test_url, test_category)

if __name__ == "__main__":
    unittest.main()
