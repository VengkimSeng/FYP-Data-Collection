#!/bin/bash

# Run crawler in background with nohup
# Usage: ./run_crawler_bg.sh [category] [num_workers]

# Get the directory of the script
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
PROJECT_ROOT="$( cd "$SCRIPT_DIR/.." && pwd )"

# Create logs directory if it doesn't exist
mkdir -p "$PROJECT_ROOT/logs"
mkdir -p "$PROJECT_ROOT/logs/categories"
mkdir -p "$PROJECT_ROOT/logs/crawlers"

# Timestamp for log file
TIMESTAMP=$(date +"%Y%m%d_%H%M%S")
LOG_FILE="$PROJECT_ROOT/logs/crawler_${TIMESTAMP}.log"

# Default number of workers
NUM_WORKERS=${2:-6}

# Change to project directory
cd "$PROJECT_ROOT" || { echo "Failed to change to project directory"; exit 1; }

echo "Starting crawler in background..."
echo "Log file: $LOG_FILE"
echo "Number of workers: $NUM_WORKERS"

if [ -z "$1" ]; then
  # Run all categories concurrently 
  # Use unbuffered Python output with the -u flag
  nohup python3 -u src/tests/test_crawler.py prod --daemon --log "$LOG_FILE" --workers "$NUM_WORKERS" >> "$LOG_FILE" 2>&1 &
else
  # Run specific category
  nohup python3 -u src/tests/test_crawler.py prod "$1" --daemon --log "$LOG_FILE" >> "$LOG_FILE" 2>&1 &
fi

# Save the PID
echo $! > "$PROJECT_ROOT/crawler.pid"
echo "Crawler running with PID: $!"
echo "To check progress: tail -f $LOG_FILE"
echo "To stop crawler: kill $(cat "$PROJECT_ROOT/crawler.pid")"

# Create a kill script for easier termination
cat > "$PROJECT_ROOT/kill_crawler.sh" << EOF
#!/bin/bash
# Kill crawler process
echo "Terminating crawler process..."
if [ -f "$PROJECT_ROOT/crawler.pid" ]; then
  PID=\$(cat "$PROJECT_ROOT/crawler.pid")
  kill \$PID 2>/dev/null || kill -9 \$PID 2>/dev/null
  rm "$PROJECT_ROOT/crawler.pid"
  echo "Crawler process terminated."
else
  echo "No crawler PID file found."
fi
EOF

chmod +x "$PROJECT_ROOT/kill_crawler.sh"
echo "Kill script created at $PROJECT_ROOT/kill_crawler.sh"
