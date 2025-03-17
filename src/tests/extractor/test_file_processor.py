#!/usr/bin/env python3
"""Test the file processor module."""

import os
import sys
import unittest
from unittest.mock import patch, MagicMock
from colorama import Fore, Style

from src.tests.extractor.test_base import BaseExtractorTest

class FileProcessorTests(BaseExtractorTest):
    """Test class for file processor functionality."""
    
    @patch('src.extractors.file_processor.get_extractor_for_domain')
    def test_process_url(self, mock_get_extractor):
        """Test processing a single URL."""
        print(f"\n{Fore.CYAN}Testing process_url function...{Style.RESET_ALL}")
        
        # Create mock extractor
        mock_extractor = MagicMock()
        mock_extractor.extract_article.return_value = {
            "title": "Test Article",
            "content": "This is a test article content.",
            "url": self.test_urls[0],
            "category": self.test_category
        }
        
        # Mock get_extractor_for_domain to return our mock
        mock_get_extractor.return_value = mock_extractor
        
        from src.extractors.file_processor import process_url
        
        # Test process_url
        result = process_url(self.test_urls[0], self.test_category, self.output_dir, verbose=True)
        
        # Check result
        self.assertIsNotNone(result)
        self.assertTrue(result['success'])
        self.assertIn('output_file', result)
        self.assertIn('duration', result)
        
        print(f"{Fore.GREEN}✓ process_url successfully processed a URL{Style.RESET_ALL}")
    
    @patch('src.extractors.file_processor.process_url')
    def test_process_file(self, mock_process_url):
        """Test processing a file of URLs."""
        print(f"\n{Fore.CYAN}Testing process_file function...{Style.RESET_ALL}")
        
        # Mock process_url to return success
        mock_process_url.return_value = {'success': True}
        
        from src.extractors.file_processor import process_file
        
        # Test process_file
        result = process_file(self.url_file, self.output_dir, verbose=True)
        
        # Check result
        self.assertIsNotNone(result)
        self.assertEqual(result['category'], self.test_category)
        self.assertEqual(result['total'], len(self.test_urls))
        self.assertEqual(result['processed'], len(self.test_urls))
        
        print(f"{Fore.GREEN}✓ process_file successfully processed a file{Style.RESET_ALL}")
    
    def test_extract_domain(self):
        """Test domain extraction from URLs."""
        print(f"\n{Fore.CYAN}Testing extract_domain function...{Style.RESET_ALL}")
        
        from src.extractors.file_processor import extract_domain
        
        test_cases = [
            ("https://www.example.com/article/123", "www.example.com"),
            ("http://example.com/test", "example.com"),
            ("https://subdomain.example.co.uk/path?query=test", "subdomain.example.co.uk"),
            ("https://www.rfa.org/khmer/news/123456", "www.rfa.org")
        ]
        
        for url, expected_domain in test_cases:
            self.assertEqual(extract_domain(url), expected_domain)
        
        print(f"{Fore.GREEN}✓ extract_domain correctly extracts domains from URLs{Style.RESET_ALL}")

if __name__ == "__main__":
    unittest.main()
