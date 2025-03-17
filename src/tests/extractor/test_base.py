#!/usr/bin/env python3
"""
Base test class for extractor tests with shared setup and teardown.
"""

import os
import sys
import unittest
import json
import tempfile
import shutil

# Add the project root to the Python path for imports
project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, project_root)

from colorama import Fore, Style, init
from unittest.mock import patch

# Initialize colorama
init(autoreset=True)

class BaseExtractorTest(unittest.TestCase):
    """Base test class with common setup/teardown for all extractor tests."""
    
    def setUp(self):
        """Set up test environment."""
        # Create temporary directories for testing
        self.temp_dir = tempfile.mkdtemp()
        self.input_dir = os.path.join(self.temp_dir, "urls")
        self.output_dir = os.path.join(self.temp_dir, "articles")
        self.checkpoint_dir = os.path.join(self.temp_dir, "checkpoints")
        
        # Create directories
        os.makedirs(self.input_dir, exist_ok=True)
        os.makedirs(self.output_dir, exist_ok=True)
        os.makedirs(self.checkpoint_dir, exist_ok=True)
        
        # Create a test URL file
        self.test_category = "test_category"
        self.test_urls = [
            "https://btv.com.kh/article/123",
            "https://www.rfa.org/khmer/news/article/456",
            "https://kohsantepheapdaily.com.kh/article/789",
            "https://www.nonexistent-domain.com/article/999"
        ]
        
        # Write test URLs to a file
        self.url_file = os.path.join(self.input_dir, f"{self.test_category}.json")
        with open(self.url_file, 'w', encoding='utf-8') as f:
            json.dump(self.test_urls, f, ensure_ascii=False)
        
        # Patch config settings
        self.config_patcher = patch('src.extractors.config.CHECKPOINT_FILE', 
                                   os.path.join(self.checkpoint_dir, "test_checkpoint.json"))
        self.mock_config = self.config_patcher.start()
        
        # Also patch the storage output directory
        self.storage_patcher = patch('src.extractors.storage._output_directory', self.output_dir)
        self.mock_storage = self.storage_patcher.start()
        
        print(f"{Fore.CYAN}Test environment set up in {self.temp_dir}{Style.RESET_ALL}")
    
    def tearDown(self):
        """Clean up after tests."""
        # Stop patches
        self.config_patcher.stop()
        self.storage_patcher.stop()
        
        # Remove temporary directory
        shutil.rmtree(self.temp_dir)
        print(f"{Fore.CYAN}Test environment cleaned up{Style.RESET_ALL}")
