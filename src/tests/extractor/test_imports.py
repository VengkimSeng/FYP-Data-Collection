#!/usr/bin/env python3
"""Test module imports for the extractor system."""

import unittest
import importlib
from colorama import Fore, Style

class ImportTests(unittest.TestCase):
    """Test imports for all extractor modules."""
    
    def test_imports(self):
        """Test that all necessary modules can be imported."""
        modules_to_test = [
            'src.extractors.utils',
            'src.extractors.browser',
            'src.extractors.logger',
            'src.extractors.file_processor',
            'src.extractors.storage',
            'src.extractors.scrapers.generic_scraper',
            'src.extractors.scrapers.extractor_adapter',
        ]
        
        for module_name in modules_to_test:
            with self.subTest(module=module_name):
                try:
                    module = importlib.import_module(module_name)
                    self.assertIsNotNone(module)
                    
                    # Check for specific critical functions in each module
                    if module_name == 'src.extractors.utils':
                        self.assertTrue(hasattr(module, 'load_checkpoint'))
                        self.assertTrue(hasattr(module, 'update_checkpoint'))
                        self.assertTrue(hasattr(module, 'is_scraped'))
                        
                    elif module_name == 'src.extractors.browser':
                        self.assertTrue(hasattr(module, 'create_driver'))
                        self.assertTrue(hasattr(module, 'close_driver'))
                        
                    elif module_name == 'src.extractors.logger':
                        self.assertTrue(hasattr(module, 'log_debug'))
                        self.assertTrue(hasattr(module, 'log_error'))
                        
                    elif module_name == 'src.extractors.file_processor':
                        self.assertTrue(hasattr(module, 'process_file'))
                        self.assertTrue(hasattr(module, 'process_url'))
                        
                    elif module_name == 'src.extractors.scrapers.generic_scraper':
                        self.assertTrue(hasattr(module, 'generic_scrape'))
                        self.assertTrue(hasattr(module, 'extract_title'))
                        self.assertTrue(hasattr(module, 'extract_content'))
                        
                    elif module_name == 'src.extractors.scrapers.extractor_adapter':
                        self.assertTrue(hasattr(module, 'create_extractor_for_domain'))
                        
                except ImportError as e:
                    self.fail(f"Failed to import {module_name}: {e}")

if __name__ == "__main__":
    unittest.main()
