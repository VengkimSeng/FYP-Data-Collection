#!/usr/bin/env python3
"""
Extractor Test Report Generator

This script converts JSON test results into a formatted markdown report.
"""

import os
import sys
import json
import datetime
import re
from collections import defaultdict
from typing import Dict, List, Any, Tuple, Set

# Add the parent directory to Python path for imports
current_dir = os.path.dirname(os.path.abspath(__file__))
tests_dir = os.path.dirname(current_dir)
src_dir = os.path.dirname(tests_dir)
project_root = os.path.dirname(src_dir)
sys.path.append(project_root)

# Test categories
TEST_CATEGORIES = {
    "Common Components": [
        "test_imports", "test_generic_scraper", "test_checkpoint_mechanism",
        "test_extract_domain", "test_process_file", "test_process_url",
        "test_output_directory_functions", "test_save_article_data",
        "test_adapter_calls_specific_scraper", "test_adapter_fallback_to_generic",
        "test_create_extractor_for_domain", "test_close_driver",
        "test_create_driver", "test_get_chrome_options",
        "test_log_debug", "test_log_error", "test_log_scrape_status"
    ],
    "Integration Tests": [
        "test_end_to_end_extraction", "test_main_module"
    ],
    "Site-Specific Scrapers": [
        "test_btv_scraper", "test_scraper_registration.BtvScraperTests",
        "test_postkhmer_scraper", "test_scraper_registration.PostKhmerScraperTests",
        "test_kohsantepheap_scraper", "test_scraper_registration.KohsantepheapScraperTests",
        "test_dapnews_scraper", "test_scraper_registration.DapNewsScraperTests",
        "test_sabay_scraper", "test_scraper_registration.SabayScraperTests",
        "test_rfa_scraper", "test_scraper_registration.RfaScraperTests"
    ]
}

# User-friendly test name mapping
TEST_NAME_MAP = {
    "test_imports": "Import test",
    "test_generic_scraper": "Generic scraper test",
    "test_checkpoint_mechanism": "Checkpoint mechanism",
    "test_extract_domain": "Extract domain",
    "test_process_file": "Process file",
    "test_process_url": "Process URL",
    "test_output_directory_functions": "Output directory functions",
    "test_save_article_data": "Save article data",
    "test_adapter_calls_specific_scraper": "Adapter calls specific scraper",
    "test_adapter_fallback_to_generic": "Adapter fallback to generic",
    "test_create_extractor_for_domain": "Create extractor for domain",
    "test_close_driver": "Close driver",
    "test_create_driver": "Create driver",
    "test_get_chrome_options": "Get Chrome options",
    "test_log_debug": "Log debug",
    "test_log_error": "Log error",
    "test_log_scrape_status": "Log scrape status",
    "test_end_to_end_extraction": "End-to-end extraction",
    "test_main_module": "Main module",
    "test_btv_scraper": "BTV scraper",
    "test_postkhmer_scraper": "PostKhmer scraper",
    "test_kohsantepheap_scraper": "Kohsantepheap scraper",
    "test_dapnews_scraper": "DapNews scraper",
    "test_sabay_scraper": "Sabay scraper",
    "test_rfa_scraper": "RFA scraper",
    "test_scraper_registration.BtvScraperTests": "BTV scraper registration",
    "test_scraper_registration.PostKhmerScraperTests": "PostKhmer scraper registration",
    "test_scraper_registration.KohsantepheapScraperTests": "Kohsantepheap scraper registration",
    "test_scraper_registration.DapNewsScraperTests": "DapNews scraper registration",
    "test_scraper_registration.SabayScraperTests": "Sabay scraper registration",
    "test_scraper_registration.RfaScraperTests": "RFA scraper registration"
}

def get_friendly_test_name(test_id: str) -> str:
    """Get a user-friendly test name from a test ID."""
    # Extract the method name from the test ID
    match = re.search(r'\.([^\.]+)$', test_id)
    if match:
        method_name = match.group(1)
        # Check if the method name with class is in the mapping
        for key, value in TEST_NAME_MAP.items():
            if key in test_id:
                return value
        # Use the method name as a fallback
        return TEST_NAME_MAP.get(method_name, method_name)
    return test_id

def categorize_test_results(results: List[Dict[str, Any]]) -> Dict[str, List[Dict[str, Any]]]:
    """Categorize test results into predefined categories."""
    categorized = {}
    
    # Initialize with empty lists
    for category in TEST_CATEGORIES.keys():
        categorized[category] = []
    
    # Assign tests to categories
    for result in results:
        test_id = result["name"]
        assigned = False
        
        for category, test_patterns in TEST_CATEGORIES.items():
            for pattern in test_patterns:
                if pattern in test_id:
                    categorized[category].append(result)
                    assigned = True
                    break
            if assigned:
                break
        
        # If not assigned to any category, put in Common Components as fallback
        if not assigned:
            categorized["Common Components"].append(result)
    
    return categorized

def format_duration(seconds: float) -> str:
    """Format a duration in seconds to a readable string."""
    if seconds < 0.01:
        return "0.00s"
    return f"{seconds:.2f}s"

def format_test_result(result: Dict[str, Any]) -> Tuple[str, str, str, str]:
    """Format a test result for display in the markdown report."""
    test_name = get_friendly_test_name(result["name"])
    
    # Format result status with emoji
    status = result["status"]
    if status == "PASS":
        status_formatted = "✅ Pass"
    elif status == "FAIL":
        status_formatted = "❌ Fail"
    else:
        status_formatted = "❌ Error"
    
    # Format duration
    duration = format_duration(result["time"])
    
    # Format error message if any
    message = result.get("error", "")
    
    return test_name, status_formatted, duration, message

def create_markdown_report(json_report_path: str) -> str:
    """Generate a markdown report from a JSON test report."""
    # Load the JSON report
    with open(json_report_path, 'r', encoding='utf-8') as f:
        report_data = json.load(f)
    
    # Extract key information
    timestamp = report_data["timestamp"]
    test_count = report_data["test_count"]
    failures = report_data["failures"]
    errors = report_data["errors"]
    results = report_data["results"]
    statistics = report_data.get("statistics", {})
    
    # Calculate statistics if not provided
    if not statistics:
        pass_count = sum(1 for r in results if r["status"] == "PASS")
        fail_count = sum(1 for r in results if r["status"] == "FAIL")
        error_count = sum(1 for r in results if r["status"] == "ERROR")
        pass_percentage = (pass_count / test_count) * 100 if test_count > 0 else 0
    else:
        pass_count = statistics["pass"]
        fail_count = statistics["fail"]
        error_count = statistics["error"]
        pass_percentage = statistics["pass_percentage"]
    
    # Build Markdown content
    markdown = "# Extractor Test Report\n\n"
    
    # Summary section
    markdown += "## Summary\n\n"
    markdown += f"- **Total Tests:** {test_count}\n"
    markdown += f"- **Passed:** {pass_count}\n"
    markdown += f"- **Failed:** {fail_count}\n"
    markdown += f"- **Errors:** {error_count}\n\n"
    markdown += f"**Success Rate:** {pass_percentage:.1f}%\n\n"
    
    # Progress bar
    progress = int(pass_percentage / 5)  # 20 chars for 100%
    markdown += "```\n"
    markdown += f"[{'=' * progress}{' ' * (20 - progress)}]\n"
    markdown += "```\n\n"
    
    # Categorize test results
    categorized_results = categorize_test_results(results)
    
    # Detailed results section
    markdown += "## Detailed Results\n\n"
    
    # Process each category
    error_details = []
    
    for category, category_results in categorized_results.items():
        if not category_results:
            continue
            
        # Calculate category statistics
        category_pass = sum(1 for r in category_results if r["status"] == "PASS")
        category_total = len(category_results)
        category_success_rate = (category_pass / category_total) * 100 if category_total > 0 else 0
        
        markdown += f"### {category}\n\n"
        markdown += f"Success Rate: {category_success_rate:.1f}% ({category_pass}/{category_total})\n\n"
        
        # Table header
        markdown += "| Test | Result | Duration | Message |\n"
        markdown += "|------|--------|----------|--------|\n"
        
        # Add table rows
        for result in category_results:
            test_name, status, duration, message = format_test_result(result)
            markdown += f"| {test_name} | {status} | {duration} | {message} |\n"
            
            # Collect error details for the error summary
            if result["status"] != "PASS" and message:
                error_details.append((test_name, message, result["status"]))
        
        markdown += "\n---\n\n"
    
    # Add error summary if there are failures or errors
    if failures > 0 or errors > 0:
        markdown += "## Error Summary\n\n"
        markdown += "The following key issues need to be addressed:\n\n"
        
        # Group similar errors and count occurrences
        grouped_errors = defaultdict(int)
        for _, error, _ in error_details:
            grouped_errors[error] += 1
        
        # Find the key issues (most common errors)
        key_issues = set()
        for test_name, error, status in error_details:
            if "unterminated string literal" in error:
                key_issues.add("**Syntax error in file_processor.py** (line 70) - unterminated string literal")
            elif "retry_on_exception" in error:
                key_issues.add("**Missing function 'retry_on_exception'** in src.extractors.utils")
            elif "SCRAPER_MAP" in error:
                key_issues.add("**Missing variable 'SCRAPER_MAP'** in src.extractors.config")
            elif "ChromeDriverManager" in error:
                key_issues.add("**Missing attribute 'ChromeDriverManager'** in browser module")
            elif "1 != 2" in error:
                key_issues.add("**Check point mechanism test failure** - expected value mismatch")
            # Add more patterns as needed
        
        # If no key issues were identified, include the top 5 most common errors
        if not key_issues:
            sorted_errors = sorted(grouped_errors.items(), key=lambda x: x[1], reverse=True)
            for i, (error, count) in enumerate(sorted_errors[:5]):
                key_issues.add(f"**Error {i+1}:** {error}")
        
        # Add the issues as a numbered list
        for i, issue in enumerate(sorted(key_issues), 1):
            markdown += f"{i}. {issue}\n"
    
    # Add timestamp
    markdown += f"\nReport generated at: {timestamp}\n"
    
    return markdown

def create_direct_markdown_report(report_data: Dict[str, Any]) -> str:
    """Generate a markdown report directly from report data dictionary.
    
    Args:
        report_data: Report data dictionary
        
    Returns:
        String containing the markdown report
    """
    # Extract key information
    timestamp = report_data["timestamp"]
    test_count = report_data["test_count"]
    failures = report_data["failures"]
    errors = report_data["errors"]
    results = report_data["results"]
    statistics = report_data.get("statistics", {})
    
    # Calculate statistics if not provided
    if not statistics:
        pass_count = sum(1 for r in results if r["status"] == "PASS")
        fail_count = sum(1 for r in results if r["status"] == "FAIL")
        error_count = sum(1 for r in results if r["status"] == "ERROR")
        pass_percentage = (pass_count / test_count) * 100 if test_count > 0 else 0
    else:
        pass_count = statistics["pass"]
        fail_count = statistics["fail"]
        error_count = statistics["error"]
        pass_percentage = statistics["pass_percentage"]
    
    # Build Markdown content
    markdown = "# Extractor Test Report\n\n"
    
    # Summary section
    markdown += "## Summary\n\n"
    markdown += f"- **Total Tests:** {test_count}\n"
    markdown += f"- **Passed:** {pass_count}\n"
    markdown += f"- **Failed:** {fail_count}\n"
    markdown += f"- **Errors:** {error_count}\n\n"
    markdown += f"**Success Rate:** {pass_percentage:.1f}%\n\n"
    
    # Progress bar
    progress = int(pass_percentage / 5)  # 20 chars for 100%
    markdown += "```\n"
    markdown += f"[{'=' * progress}{' ' * (20 - progress)}]\n"
    markdown += "```\n\n"
    
    # Categorize test results
    categorized_results = categorize_test_results(results)
    
    # Detailed results section
    markdown += "## Detailed Results\n\n"
    
    # Process each category
    error_details = []
    
    for category, category_results in categorized_results.items():
        if not category_results:
            continue
            
        # Calculate category statistics
        category_pass = sum(1 for r in category_results if r["status"] == "PASS")
        category_total = len(category_results)
        category_success_rate = (category_pass / category_total) * 100 if category_total > 0 else 0
        
        markdown += f"### {category}\n\n"
        markdown += f"Success Rate: {category_success_rate:.1f}% ({category_pass}/{category_total})\n\n"
        
        # Table header
        markdown += "| Test | Result | Duration | Message |\n"
        markdown += "|------|--------|----------|--------|\n"
        
        # Add table rows
        for result in category_results:
            test_name, status, duration, message = format_test_result(result)
            markdown += f"| {test_name} | {status} | {duration} | {message} |\n"
            
            # Collect error details for the error summary
            if result["status"] != "PASS" and message:
                error_details.append((test_name, message, result["status"]))
        
        markdown += "\n---\n\n"
    
    # Add error summary if there are failures or errors
    if failures > 0 or errors > 0:
        markdown += "## Error Summary\n\n"
        markdown += "The following key issues need to be addressed:\n\n"
        
        # Group similar errors and count occurrences
        grouped_errors = defaultdict(int)
        for _, error, _ in error_details:
            grouped_errors[error] += 1
        
        # Find the key issues (most common errors)
        key_issues = set()
        for test_name, error, status in error_details:
            if "unterminated string literal" in error:
                key_issues.add("**Syntax error in file_processor.py** (line 70) - unterminated string literal")
            elif "retry_on_exception" in error:
                key_issues.add("**Missing function 'retry_on_exception'** in src.extractors.utils")
            elif "SCRAPER_MAP" in error:
                key_issues.add("**Missing variable 'SCRAPER_MAP'** in src.extractors.config")
            elif "ChromeDriverManager" in error:
                key_issues.add("**Missing attribute 'ChromeDriverManager'** in browser module")
            elif "1 != 2" in error:
                key_issues.add("**Check point mechanism test failure** - expected value mismatch")
            # Add more patterns as needed
        
        # If no key issues were identified, include the top 5 most common errors
        if not key_issues:
            sorted_errors = sorted(grouped_errors.items(), key=lambda x: x[1], reverse=True)
            for i, (error, count) in enumerate(sorted_errors[:5]):
                key_issues.add(f"**Error {i+1}:** {error}")
        
        # Add the issues as a numbered list
        for i, issue in enumerate(sorted(key_issues), 1):
            markdown += f"{i}. {issue}\n"
    
    # Add timestamp
    markdown += f"\nReport generated at: {timestamp}\n"
    
    return markdown