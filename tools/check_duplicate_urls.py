#!/usr/bin/env python3

import os
import sys
import json
import argparse
import shutil
from collections import Counter
from colorama import Fore, Style, init

# Initialize colorama
init()

def check_duplicates(file_path, remove_duplicates=False):
    """Check a specific file for duplicate URLs and report statistics."""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            try:
                data = json.load(f)
                original_data = data  # Store the original structure
            except json.JSONDecodeError:
                print(f"{Fore.RED}Error: {file_path} is not a valid JSON file{Style.RESET_ALL}")
                return
        
        # Handle different JSON structures
        original_structure = None  # To track if we have a list or dict
        if isinstance(data, list):
            urls = data
            original_structure = "list"
        elif isinstance(data, dict):
            # Extract URLs from nested structures if necessary
            urls = []
            original_structure = "dict"
            def extract_urls(obj):
                if isinstance(obj, dict):
                    for key, value in obj.items():
                        if isinstance(value, str) and value.startswith("http"):
                            urls.append(value)
                        elif isinstance(value, (list, dict)):
                            extract_urls(value)
                elif isinstance(obj, list):
                    for item in obj:
                        extract_urls(item)
            
            extract_urls(data)
        else:
            print(f"{Fore.RED}Error: Unsupported data structure in {file_path}{Style.RESET_ALL}")
            return
        
        # Find duplicates
        url_counts = Counter(urls)
        duplicates = {url: count for url, count in url_counts.items() if count > 1}
        
        # Report results
        total_urls = len(urls)
        unique_urls = len(set(urls))
        duplicate_count = len(duplicates)
        
        print(f"\n{Fore.CYAN}=== File: {file_path} ==={Style.RESET_ALL}")
        print(f"Total URLs: {total_urls}")
        print(f"Unique URLs: {unique_urls}")
        
        if duplicate_count > 0:
            print(f"{Fore.YELLOW}Duplicate URLs found: {duplicate_count}{Style.RESET_ALL}")
            if args.show_duplicates:
                print(f"\n{Fore.YELLOW}Duplicates:{Style.RESET_ALL}")
                for url, count in duplicates.items():
                    print(f"  {url} ({count} occurrences)")
            
            if args.create_clean:
                output_path = file_path.replace('.json', '_clean.json')
                with open(output_path, 'w', encoding='utf-8') as f:
                    json.dump(list(set(urls)), f, indent=2)
                print(f"{Fore.GREEN}Clean file created: {output_path}{Style.RESET_ALL}")
            
            if remove_duplicates:
                # Create a backup first
                backup_path = file_path + '.bak'
                shutil.copy2(file_path, backup_path)
                
                # Handle according to original structure
                if original_structure == "list":
                    # Simply replace with unique URLs
                    unique_urls_list = list(set(urls))
                    with open(file_path, 'w', encoding='utf-8') as f:
                        json.dump(unique_urls_list, f, indent=2)
                        
                elif original_structure == "dict":
                    # This is tricky as we need to modify nested structures
                    # For now, let's just warn the user that dict structures 
                    # are not supported for direct modification
                    print(f"{Fore.YELLOW}Warning: Direct modification of dictionary structures is not supported.{Style.RESET_ALL}")
                    print(f"{Fore.YELLOW}A clean list version has been created as {file_path.replace('.json', '_clean.json')}{Style.RESET_ALL}")
                    with open(file_path.replace('.json', '_clean.json'), 'w', encoding='utf-8') as f:
                        json.dump(list(set(urls)), f, indent=2)
                    return total_urls, unique_urls, duplicate_count
                
                print(f"{Fore.GREEN}Removed {total_urls - unique_urls} duplicate URLs from {file_path}{Style.RESET_ALL}")
                print(f"{Fore.GREEN}Backup saved to {backup_path}{Style.RESET_ALL}")
        else:
            print(f"{Fore.GREEN}No duplicates found!{Style.RESET_ALL}")
        
        return total_urls, unique_urls, duplicate_count
    
    except Exception as e:
        print(f"{Fore.RED}Error processing {file_path}: {str(e)}{Style.RESET_ALL}")
        return 0, 0, 0

def scan_directory(directory, remove_duplicates=False):
    """Scan all JSON files in a directory for duplicates."""
    total_stats = {
        'total_files': 0,
        'total_urls': 0,
        'total_unique_urls': 0,
        'files_with_duplicates': 0,
        'total_duplicates': 0
    }
    
    for root, _, files in os.walk(directory):
        for file in files:
            if file.endswith('.json'):
                file_path = os.path.join(root, file)
                
                stats = check_duplicates(file_path, remove_duplicates)
                if stats:
                    total_urls, unique_urls, duplicate_count = stats
                    total_stats['total_files'] += 1
                    total_stats['total_urls'] += total_urls
                    total_stats['total_unique_urls'] += unique_urls
                    
                    if duplicate_count > 0:
                        total_stats['files_with_duplicates'] += 1
                        total_stats['total_duplicates'] += duplicate_count
    
    print(f"\n{Fore.CYAN}=== Summary ==={Style.RESET_ALL}")
    print(f"Processed {total_stats['total_files']} JSON files")
    print(f"Total URLs: {total_stats['total_urls']}")
    print(f"Total unique URLs: {total_stats['total_unique_urls']}")
    print(f"Files with duplicates: {total_stats['files_with_duplicates']}")
    print(f"Total duplicate URLs: {total_stats['total_duplicates']}")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Check for duplicate URLs in JSON files.")
    parser.add_argument('path', nargs='?', default=None, help='Path to a JSON file or directory')
    parser.add_argument('--create-clean', '-c', action='store_true', help='Create a clean version without duplicates')
    parser.add_argument('--show-duplicates', '-s', action='store_true', help='Show the duplicate URLs')
    parser.add_argument('--scan-dir', '-d', action='store_true', help='Scan an entire directory recursively')
    parser.add_argument('--remove-duplicates', '-r', action='store_true', help='Remove duplicates from the original files')
    args = parser.parse_args()
    
    path = args.path or os.getcwd()
    
    if args.remove_duplicates:
        confirm = input(f"{Fore.YELLOW}WARNING: This will modify original files. Backups will be created with .bak extension.\nContinue? (y/N): {Style.RESET_ALL}")
        if confirm.lower() != 'y':
            print("Operation cancelled.")
            sys.exit(0)
    
    if args.scan_dir or os.path.isdir(path):
        scan_directory(path, args.remove_duplicates)
    elif os.path.isfile(path):
        check_duplicates(path, args.remove_duplicates)
    else:
        print(f"{Fore.RED}Error: Path {path} does not exist{Style.RESET_ALL}")
        sys.exit(1)
