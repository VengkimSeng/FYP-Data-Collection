#!/bin/bash

echo "Starting repository reorganization..."

# Check if we have a clean git state
if [ -d ".git" ]; then
  if [ -n "$(git status --porcelain)" ]; then
    echo "Warning: You have uncommitted changes. It's recommended to commit changes before reorganizing."
    read -p "Do you want to continue anyway? (y/n) " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
      echo "Reorganization cancelled."
      exit 1
    fi
  fi
fi

# Make the scripts executable
chmod +x reorganize.sh update_imports.py

# Run the reorganization script
./reorganize.sh

# Make sure all directories exist
mkdir -p output/logs/categories
mkdir -p output/logs/errors

# Run the import updater
python3 update_imports.py

# Create symbolic links for backward compatibility
echo "Creating symbolic links for backward compatibility..."
ln -sf config/categories.json categories.json
ln -sf src/extractors/article_crawler.py A_Overall_Article_Crawler.py
ln -sf src/crawlers/master_crawler_controller.py master_crawler_controller.py
ln -sf tools/workflow_runner.py run_complete_workflow.py
ln -sf tools/cli.py run_workflow_cli.py

echo "Reorganization complete! The repository now has a more structured layout."
echo ""
echo "You can now use the tools with the new paths:"
echo "  - Run workflow: python3 tools/cli.py all"
echo "  - Collect URLs: python3 src/crawlers/master_crawler_controller.py"
echo "  - Extract articles: python3 src/extractors/article_crawler.py"
echo ""
echo "Old command paths will continue to work through symbolic links."
