#!/usr/bin/env python3
"""Tests for the extractor utility functions."""

import os
import unittest
import tempfile
from unittest.mock import patch, MagicMock

from src.extractors.utils import load_checkpoint, update_checkpoint, retry_on_exception, is_scraped

class CheckpointTests(unittest.TestCase):
    """Test cases for checkpoint mechanism."""
    
    def setUp(self):
        # Create a temporary file for checkpoint testing
        self.temp_dir = tempfile.TemporaryDirectory()
        self.checkpoint_file = os.path.join(self.temp_dir.name, "test_checkpoint.json")
        
        # Patch the CHECKPOINT_FILE constant
        self.patcher = patch('src.extractors.utils.CHECKPOINT_FILE', self.checkpoint_file)
        self.patcher.start()
        
    def tearDown(self):
        self.patcher.stop()
        self.temp_dir.cleanup()
        
    def test_checkpoint_mechanism(self):
        """Test checkpoint saving and loading."""
        # Initially empty
        checkpoint = load_checkpoint()
        self.assertEqual(checkpoint, {})
        
        # Update with initial test data
        test_data = {'processed_urls': ['url1', 'url2', 'url3']}  # Include all three URLs initially
        result = update_checkpoint(test_data)
        self.assertTrue(result)
        
        # Verify checkpoint was saved with all three URLs
        checkpoint = load_checkpoint()
        self.assertEqual(checkpoint, test_data)
        self.assertEqual(len(checkpoint['processed_urls']), 3)
        
        # Verify each URL is present
        self.assertIn('url1', checkpoint['processed_urls'])
        self.assertIn('url2', checkpoint['processed_urls'])
        self.assertIn('url3', checkpoint['processed_urls'])
        
    def test_is_scraped(self):
        """Test is_scraped function."""
        # Set up test data
        test_data = {
            'processed_urls': ['url1', 'url2'],
            'category_urls': {
                'sports': ['url3', 'url4'],
                'politics': ['url5']
            }
        }
        update_checkpoint(test_data)
        
        # Check global URLs
        self.assertTrue(is_scraped('url1'))
        self.assertTrue(is_scraped('url2'))
        self.assertFalse(is_scraped('url6'))
        
        # Check category-specific URLs
        self.assertTrue(is_scraped('url3', 'sports'))
        self.assertTrue(is_scraped('url5', 'politics'))
        self.assertFalse(is_scraped('url1', 'sports'))  # url1 is global but not in sports

# Add more test classes for other utilities if needed

if __name__ == "__main__":
    unittest.main()
