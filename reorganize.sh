#!/bin/bash

echo "Creating new directory structure..."

# Create main directories
mkdir -p src/crawlers
mkdir -p src/extractors
mkdir -p src/utils
mkdir -p config
mkdir -p output/urls
mkdir -p output/articles
mkdir -p output/logs
mkdir -p tools

# Move crawler files
echo "Moving crawler files..."
mv "1- URL-improve"/*.py src/crawlers/
mv "master_crawler_controller.py" src/crawlers/
mv "url_saver.py" src/utils/

# Move extractor files
echo "Moving article extraction files..."
mv "A_Overall_Article_Crawler.py" src/extractors/article_crawler.py
mv "article_crawler"/*.py src/extractors/
mv "article_crawler/scrapers" src/extractors/

# Move utility files
echo "Moving utility files..."
mv "chrome_setup.py" src/utils/
mv "run_complete_workflow.py" tools/workflow_runner.py
mv "run_workflow_cli.py" tools/cli.py
mv "sync_category_urls.py" tools/sync_categories.py

# Move configuration files
echo "Moving configuration files..."
mv "categories.json" config/

# Create empty output directories to maintain structure
touch output/urls/.gitkeep
touch output/articles/.gitkeep
touch output/logs/.gitkeep

echo "Reorganization complete!"
