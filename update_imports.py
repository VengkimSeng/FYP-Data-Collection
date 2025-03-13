#!/usr/bin/env python3
"""
Update import statements in Python files to reflect the new directory structure.
"""

import os
import re
import sys
from pathlib import Path

def update_imports(file_path):
    """Update import statements in a Python file."""
    try:
        with open(file_path, 'r', encoding='utf-8') as file:
            content = file.read()
        
        # Update relative imports for crawler files
        if 'src/crawlers' in str(file_path):
            # Update url_saver imports
            content = re.sub(
                r'from url_saver import', 
                r'from src.utils.url_saver import',
                content
            )
            # Update chrome_setup imports
            content = re.sub(
                r'from chrome_setup import', 
                r'from src.utils.chrome_setup import',
                content
            )
            
        # Update relative imports for extractor files
        if 'src/extractors' in str(file_path):
            # Update logger/utils/storage imports within the extractors
            content = re.sub(
                r'from (\.?)(logger|utils|storage|config|file_processor|url_processor) import', 
                r'from src.extractors.\2 import',
                content
            )
            # Update scrapers import
            content = re.sub(
                r'from scrapers import', 
                r'from src.extractors.scrapers import',
                content
            )
            
        # Update imports in tool files
        if 'tools' in str(file_path):
            content = re.sub(
                r'from (A_Overall_Article_Crawler|master_crawler_controller|sync_category_urls) import', 
                lambda m: f'from src.extractors.article_crawler import' if m.group(1) == 'A_Overall_Article_Crawler' 
                         else f'from src.crawlers.master_crawler_controller import' if m.group(1) == 'master_crawler_controller'
                         else f'from tools.sync_categories import',
                content
            )
            
        # Update config paths
        content = re.sub(
            r'["\'](categories.json)["\']', 
            r'"config/\1"',
            content
        )
        
        # Update output directory references
        content = re.sub(
            r'["\'](Scrape_urls|Selected_URLs)["\']', 
            r'"output/urls"',
            content
        )
        content = re.sub(
            r'["\'](Article)["\']', 
            r'"output/articles"',
            content
        )
        content = re.sub(
            r'["\'](Category_Logs)["\']', 
            r'"output/logs/categories"',
            content
        )
        content = re.sub(
            r'["\'](Category_Errors)["\']', 
            r'"output/logs/errors"',
            content
        )
        
        with open(file_path, 'w', encoding='utf-8') as file:
            file.write(content)
        print(f"Updated imports in {file_path}")
            
    except Exception as e:
        print(f"Error updating imports in {file_path}: {e}")
        return False
    
    return True

def main():
    """Main function to update all Python files."""
    base_dir = Path(__file__).parent
    
    # Find all Python files in the new directory structure
    py_files = []
    for directory in ['src', 'tools']:
        dir_path = base_dir / directory
        if dir_path.exists():
            py_files.extend(dir_path.glob('**/*.py'))
    
    updated = 0
    failed = 0
    
    for file_path in py_files:
        if update_imports(file_path):
            updated += 1
        else:
            failed += 1
    
    print(f"\nImport update completed: {updated} files updated, {failed} files failed.")
    
if __name__ == "__main__":
    main()
