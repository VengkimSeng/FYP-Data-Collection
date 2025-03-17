#!/bin/bash

# Script to run environment crawler in the background
cd /home/root/FYP-Data-Collection/FYP-Data-Collection/
echo "Starting environment crawler at $(date)" >> output/logs/environment_crawler.log

# Create logs directory if it doesn't exist
mkdir -p output/logs

# Run the crawler with nohup to keep it running after logout
nohup python3 src/crawlers/master_crawler_controller.py \
  --category environment \
  --output-dir output/urls \
  --workers 2 \
  --max-urls-per-category 2500 \
  >> output/logs/environment_crawler.log 2>&1 &

echo "Crawler started with PID $!" >> output/logs/environment_crawler.log
echo $! > output/logs/environment_crawler.pid
