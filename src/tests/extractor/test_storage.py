#!/usr/bin/env python3
"""Test the storage module."""

import os
import json
import unittest
from colorama import Fore, Style

from src.tests.extractor.test_base import BaseExtractorTest

class StorageTests(BaseExtractorTest):
    """Test class for storage functionality."""
    
    def test_output_directory_functions(self):
        """Test setting and getting the output directory."""
        print(f"\n{Fore.CYAN}Testing output directory functions...{Style.RESET_ALL}")
        
        from src.extractors.storage import set_output_directory, get_output_directory
        
        # Test setting and getting the output directory
        test_dir = os.path.join(self.temp_dir, "test_output")
        set_output_directory(test_dir)
        self.assertEqual(get_output_directory(), test_dir)
        self.assertTrue(os.path.exists(test_dir))
        
        print(f"{Fore.GREEN}✓ set_output_directory and get_output_directory work properly{Style.RESET_ALL}")
    
    def test_save_article_data(self):
        """Test saving article data."""
        print(f"\n{Fore.CYAN}Testing save_article_data function...{Style.RESET_ALL}")
        
        from src.extractors.storage import save_article_data, get_output_directory
        
        # Set up test data
        test_category = "test_storage"
        test_article = {
            "title": "Test Storage Article",
            "content": "This is a test of the storage system.",
            "url": "https://example.com/test-storage",
            "category": test_category
        }
        
        # Save the article
        save_article_data(test_category, test_article, "https://example.com/test-storage")
        
        # Check if the file was created
        output_dir = get_output_directory()
        expected_file = os.path.join(output_dir, f"{test_category}.json")
        self.assertTrue(os.path.exists(expected_file))
        
        # Read and validate the content
        with open(expected_file, 'r', encoding='utf-8') as f:
            saved_data = json.load(f)
            self.assertEqual(len(saved_data), 1)
            self.assertEqual(saved_data[0]["title"], "Test Storage Article")
            self.assertEqual(saved_data[0]["url"], "https://example.com/test-storage")
        
        # Test appending to existing file
        second_article = {
            "title": "Second Test Article",
            "content": "This is a second test article.",
            "url": "https://example.com/test2",
            "category": test_category
        }
        
        save_article_data(test_category, second_article, "https://example.com/test2")
        
        # Verify both articles are saved
        with open(expected_file, 'r', encoding='utf-8') as f:
            saved_data = json.load(f)
            self.assertEqual(len(saved_data), 2)
            self.assertEqual(saved_data[1]["title"], "Second Test Article")
        
        print(f"{Fore.GREEN}✓ save_article_data successfully saved articles{Style.RESET_ALL}")

if __name__ == "__main__":
    unittest.main()
