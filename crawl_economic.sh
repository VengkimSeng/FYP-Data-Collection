#!/bin/bash

# Capture current date and time for log file naming
DATE=$(date +"%Y%m%d_%H%M%S")
LOG_DIR="output/logs"
LOG_FILE="${LOG_DIR}/economic_crawler_${DATE}.log"

# Create log directory if it doesn't exist
mkdir -p $LOG_DIR

# Echo some information to the log file
echo "Starting economic category crawler at $(date)" > $LOG_FILE
echo "Target: 2534 unique URLs" >> $LOG_FILE
echo "====================================" >> $LOG_FILE

# Create PID file for monitoring
echo $$ > crawler.pid

# Run the crawler for economic category using test_crawler.py
nohup python3 src/tests/test_crawler.py prod economic \
  --daemon \
  --log "$LOG_FILE" \
  --workers 3 \
  --timeout 7200 \
  >> $LOG_FILE 2>&1 &

CRAWLER_PID=$!

# Output message to console
echo "Crawler started in background with PID: $CRAWLER_PID"
echo "Logs are being written to: $LOG_FILE"
echo "You can monitor progress with: tail -f $LOG_FILE"
echo "Will automatically stop when reaching 2534 URLs"

# Monitor URL count and stop when reaching target
echo "Starting URL count monitor..."
(
  while true; do
    if [ -f "output/urls/economic.json" ]; then
      # Count URLs in the JSON file
      URL_COUNT=$(cat output/urls/economic.json | grep -o "\"http" | wc -l)
      echo "$(date): Current URL count: $URL_COUNT" >> "$LOG_FILE"
      
      # Stop when reaching 2534 URLs
      if [ $URL_COUNT -ge 2534 ]; then
        echo "$(date): Reached target of 2534 URLs. Stopping crawler." >> "$LOG_FILE"
        echo "Target of 2534 URLs reached. Stopping crawler."
        
        # Kill the crawler process
        kill $CRAWLER_PID 2>/dev/null || kill -9 $CRAWLER_PID 2>/dev/null
        exit 0
      fi
    else
      echo "$(date): Waiting for output file to be created..." >> "$LOG_FILE"
    fi
    
    # Check every 30 seconds
    sleep 30
  done
) &

echo "Use ./kill_crawler.sh to terminate the crawler if needed"
