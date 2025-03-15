#!/bin/bash

# Run crawler in background with nohup
# Usage: ./run_crawler_bg.sh [category]

# Get the directory of the script
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
PROJECT_ROOT="$( cd "$SCRIPT_DIR/.." && pwd )"

# Create logs directory if it doesn't exist
mkdir -p "$PROJECT_ROOT/logs"

# Timestamp for log file
TIMESTAMP=$(date +"%Y%m%d_%H%M%S")
LOG_FILE="$PROJECT_ROOT/logs/crawler_${TIMESTAMP}.log"

# Change to project directory
cd "$PROJECT_ROOT" || { echo "Failed to change to project directory"; exit 1; }

echo "Starting crawler in background..."
echo "Log file: $LOG_FILE"

if [ -z "$1" ]; then
  # Run all categories
  nohup python3 src/tests/test_crawler.py prod --daemon --log "$LOG_FILE" > /dev/null 2>&1 &
else
  # Run specific category
  nohup python3 src/tests/test_crawler.py prod "$1" --daemon --log "$LOG_FILE" > /dev/null 2>&1 &
fi

# Save the PID
echo $! > "$PROJECT_ROOT/crawler.pid"
echo "Crawler running with PID: $!"
echo "To check progress: tail -f $LOG_FILE"
echo "To stop crawler: kill $(cat "$PROJECT_ROOT/crawler.pid")"
