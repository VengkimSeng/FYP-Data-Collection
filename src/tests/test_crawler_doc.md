# Crawler Testing Documentation

This document provides guidance on how to use the `test_crawler.py` tool to validate the functionality of web crawlers in the FYP-Data-Collection project.

## Overview

The test system allows you to validate:

- Individual crawlers
- Specific crawler-category combinations
- The master crawler controller
- URL saving functionality

Tests are organized as a checklist that runs through various components of the crawling system to ensure everything is functioning correctly.

## Setup

Before running tests, ensure your environment is properly set up:

1. Install all required dependencies
2. Ensure your `config/` directory has properly configured `categories.json` and `sources.json` files
3. Make sure your `output/logs` directory exists (created automatically if needed)

## Running Tests

### Command Line Options

The testing tool accepts various command line arguments:

```bash
python src/tests/test_crawler.py [options]
```

Options:

- `--crawler CRAWLER`: Test a specific crawler (e.g., btv, postkhmer)
- `--category CATEGORY`: Test a specific category (e.g., sport, politic)
- `--crawlers CRAWLER [CRAWLER ...]`: Test multiple crawlers
- `--categories CATEGORY [CATEGORY ...]`: Test multiple categories
- `--output-dir DIR`: Directory to save URLs (default: output/urls)
- `--reset`: Reset output directory before testing
- `--full`: Run full test checklist on all crawlers and categories
- `--report`: Generate detailed test report
- `--parallel`: Run tests in parallel
- `--workers N`: Number of worker threads for parallel testing (default: 2)
- `--no-confirm`: Skip confirmation prompts
- `--quick`: Run only quick tests (module imports and function checks)

### Example Commands

Test a single crawler for a specific category:

```bash
python src/tests/test_crawler.py --crawler btv --category sport
```

Test multiple crawlers with specific categories:

```bash
python src/tests/test_crawler.py --crawlers btv dapnews --categories sport politic
```

Run a full test suite and generate a report:

```bash
python src/tests/test_crawler.py --full --report
```

Reset the output directory and run tests in parallel:

```bash
python src/tests/test_crawler.py --reset --parallel --workers 4
```

## Test Cases

The test system runs the following checks for each crawler-category combination:

1. **Module Import Test**: Checks if the crawler module can be imported
2. **Function Existence Test**: Verifies the crawler has the required functions
3. **Source URL Test**: Checks if source URLs can be retrieved for the category
4. **URL Filtering Test**: Tests the URL filtering functionality
5. **Minimal Crawl Test**: Performs a minimal crawl to verify functionality
6. **URL Saving Test**: Tests if URLs can be saved properly

For the master controller, the test verifies:

1. Importing the controller module
2. Initializing the controller
3. Crawler discovery

## Test Reports

When using the `--report` option, the system generates a detailed Markdown report that includes:

- Overall test statistics
- Success/failure rates
- Detailed results for each test
- Error information with line numbers for failed tests

Reports are saved in the `output/test_reports` directory with a timestamp in the filename.

## Interpreting Results

The test system provides both console output and a detailed report:

### Console Output

- Summary statistics of tests run
- List of failed tests with error details
- Error locations with file paths and line numbers

### Report Format

The generated report includes:

1. **Summary**: Overall statistics with progress visualization
2. **Detailed Results**: Organized by crawler and category
   - Success rate for each crawler-category combination
   - Details for each test (success/failure)
   - Error locations and details for failed tests
3. **Timestamp**: When the report was generated

## Error Resolution

When tests fail, the reports provide specific information to help resolve issues:

1. Check the error location (file path and line number)
2. Review the error details provided
3. Verify that required source URLs are configured in `sources.json`
4. Ensure the crawler's extraction and filtering logic is working correctly

## Advanced Usage

### Running Tests in Parallel

For faster testing of multiple crawlers, use the `--parallel` option:

```bash
python src/tests/test_crawler.py --full --parallel --workers 4
```

This runs tests for different crawler-category combinations concurrently, which is useful for testing many crawlers at once.

### Quick Tests

To perform only basic tests (import and function checks):

```bash
python src/tests/test_crawler.py --quick
```

This is useful for a rapid check of crawler integrity without performing actual web requests.

### Resetting Output Directory

To clear previous test data:

```bash
python src/tests/test_crawler.py --reset
```

This removes all files in the output directory before running tests.

## Integration with Development Workflow

It's recommended to run crawler tests:

1. After making changes to any crawler
2. After updating the source URLs configuration
3. Before deploying to production
4. Periodically to verify continued functioning of crawlers

## Troubleshooting Common Issues

### WebDriver Issues

If tests fail with WebDriver-related errors:

- Ensure Chrome/ChromeDriver is properly installed
- Update ChromeDriver to match your Chrome version

### Network-Related Failures

If crawlers fail to retrieve URLs:

- Check your internet connection
- Verify the source URLs are accessible
- Check if the website structure has changed

### Source Configuration Issues

If no source URLs can be found:

- Verify the category exists in `categories.json`
- Ensure sources are properly configured in `sources.json`
- Check that the site name matches the crawler name

## Adding New Tests

To add new tests to the test system:

1. Create a new test function in `test_crawler.py`
2. Follow the pattern of existing tests
3. Return a `TestResult` object with success/failure information
4. Add your test to the appropriate checklist function
