#!/bin/bash

# Script to run the Article Crawler
# This processes all categories once and exits when complete

# Set error handling
set -e

# Define colors for output
GREEN='\033[0;32m'
YELLOW='\033[0;33m'
RED='\033[0;31m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Define paths
PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
CRAWLER_SCRIPT="$PROJECT_ROOT/src/A_Overall_Article_Crawler.py"
LOG_DIR="$PROJECT_ROOT/output/logs/Article"
RUNTIME_LOG="$LOG_DIR/runtime.log"
CHECKPOINT_DIR="$PROJECT_ROOT/output/checkpoint"
PID_FILE="$LOG_DIR/crawler.pid"

# Parse command line arguments
BACKGROUND=false
FORCE=false

for arg in "$@"; do
    case $arg in
        --background|-b)
            BACKGROUND=true
            shift
            ;;
        --force|-f)
            FORCE=true
            shift
            ;;
        --help|-h)
            echo -e "${BLUE}Usage: $0 [options] [crawler options]${NC}"
            echo -e "${YELLOW}Options:${NC}"
            echo "  --background, -b    Run the crawler in the background"
            echo "  --force, -f         Force start (kill existing process if running)"
            echo "  --help, -h          Show this help message"
            echo -e "${YELLOW}Any additional arguments will be passed to the crawler script${NC}"
            exit 0
            ;;
    esac
done

# Check if already running
check_running() {
    if [ -f "$PID_FILE" ]; then
        EXISTING_PID=$(cat "$PID_FILE")
        if ps -p "$EXISTING_PID" > /dev/null; then
            return 0  # Process is running
        else
            echo -e "${YELLOW}PID file exists but process is not running. Cleaning up...${NC}"
            rm -f "$PID_FILE"
            return 1  # Process is not running
        fi
    fi
    return 1  # Process is not running
}

# Kill running process
kill_running() {
    if [ -f "$PID_FILE" ]; then
        EXISTING_PID=$(cat "$PID_FILE")
        if ps -p "$EXISTING_PID" > /dev/null; then
            echo -e "${YELLOW}Killing existing crawler process (PID: $EXISTING_PID)...${NC}"
            kill "$EXISTING_PID" 2>/dev/null || kill -9 "$EXISTING_PID" 2>/dev/null
            sleep 2
            if ps -p "$EXISTING_PID" > /dev/null; then
                echo -e "${RED}Failed to kill existing process.${NC}"
                return 1
            else
                echo -e "${GREEN}Existing process terminated.${NC}"
                rm -f "$PID_FILE"
                return 0
            fi
        else
            rm -f "$PID_FILE"
            return 0
        fi
    fi
    return 0
}

# Ensure required directories exist
mkdir -p "$LOG_DIR"
mkdir -p "$PROJECT_ROOT/output/urls"
mkdir -p "$PROJECT_ROOT/output/articles"
mkdir -p "$CHECKPOINT_DIR"

echo -e "${BLUE}=== Khmer News Article Crawler ===${NC}"

# Check if already running
if check_running; then
    if [ "$FORCE" = true ]; then
        echo -e "${YELLOW}Crawler already running (PID: $(cat "$PID_FILE")). Force flag set...${NC}"
        if ! kill_running; then
            echo -e "${RED}Failed to kill existing process. Cannot continue.${NC}"
            exit 1
        fi
    else
        echo -e "${RED}Error: Crawler is already running (PID: $(cat "$PID_FILE"))${NC}"
        echo -e "${YELLOW}Use --force or -f to forcibly restart, or check the process status${NC}"
        exit 1
    fi
fi

# Check for ChromeDriver availability
check_chromedriver() {
    echo -e "${BLUE}Checking ChromeDriver availability...${NC}" | tee -a "$RUNTIME_LOG"
    
    if command -v chromedriver > /dev/null; then
        CHROMEDRIVER_VERSION=$(chromedriver --version | head -n 1)
        echo -e "${GREEN}✓ ChromeDriver found: $CHROMEDRIVER_VERSION${NC}" | tee -a "$RUNTIME_LOG"
        
        # Check if Chrome browser is installed too
        if command -v google-chrome > /dev/null; then
            CHROME_VERSION=$(google-chrome --version | head -n 1)
            echo -e "${GREEN}✓ Chrome browser found: $CHROME_VERSION${NC}" | tee -a "$RUNTIME_LOG"
        elif command -v chromium-browser > /dev/null; then
            CHROME_VERSION=$(chromium-browser --version | head -n 1)
            echo -e "${GREEN}✓ Chromium browser found: $CHROME_VERSION${NC}" | tee -a "$RUNTIME_LOG"
        else
            echo -e "${YELLOW}⚠️ ChromeDriver found but could not detect Chrome/Chromium browser${NC}" | tee -a "$RUNTIME_LOG"
            echo -e "${YELLOW}Ensure Chrome or Chromium is installed and compatible with ChromeDriver${NC}" | tee -a "$RUNTIME_LOG"
        fi
    else
        echo -e "${YELLOW}⚠️ ChromeDriver not found in PATH${NC}" | tee -a "$RUNTIME_LOG"
        
        # Detect platform and suggest installation method
        if [[ "$OSTYPE" == "linux-gnu"* ]]; then
            echo -e "${YELLOW}On Ubuntu/Debian Linux, install ChromeDriver with:${NC}" | tee -a "$RUNTIME_LOG"
            echo -e "${YELLOW}  sudo apt update && sudo apt install -y chromium-chromedriver${NC}" | tee -a "$RUNTIME_LOG"
            echo -e "${YELLOW}  or: sudo apt update && sudo apt install -y chromium-driver${NC}" | tee -a "$RUNTIME_LOG"
        elif [[ "$OSTYPE" == "darwin"* ]]; then
            echo -e "${YELLOW}On macOS, install ChromeDriver with:${NC}" | tee -a "$RUNTIME_LOG"
            echo -e "${YELLOW}  brew install --cask chromedriver${NC}" | tee -a "$RUNTIME_LOG"
        else
            echo -e "${YELLOW}Please download ChromeDriver from:${NC}" | tee -a "$RUNTIME_LOG"
            echo -e "${YELLOW}  https://chromedriver.chromium.org/downloads${NC}" | tee -a "$RUNTIME_LOG"
            echo -e "${YELLOW}Make sure it matches your Chrome version!${NC}" | tee -a "$RUNTIME_LOG"
        fi
        
        echo -e "${YELLOW}The script will attempt to continue using selenium-manager...${NC}" | tee -a "$RUNTIME_LOG"
    fi
}

# Check for ChromeDriver before starting
check_chromedriver

# Background running function
run_in_background() {
    START_TIME=$(date +"%Y-%m-%d %H:%M:%S")
    echo -e "${GREEN}[$START_TIME] Starting article crawler in background...${NC}" | tee -a "$RUNTIME_LOG"
    
    # Create a detached process with nohup
    nohup python3 "$CRAWLER_SCRIPT" "$@" >> "$RUNTIME_LOG" 2>&1 &
    
    # Get the PID and save it
    CRAWLER_PID=$!
    echo "$CRAWLER_PID" > "$PID_FILE"
    
    echo -e "${GREEN}Crawler started in background with PID: $CRAWLER_PID${NC}" | tee -a "$RUNTIME_LOG"
    echo -e "${YELLOW}You can monitor logs with: tail -f $RUNTIME_LOG${NC}"
    echo -e "${YELLOW}To stop the crawler, run: kill $CRAWLER_PID${NC}"
    echo -e "${YELLOW}Or use the script with --force to restart: $0 --force${NC}"
}

# Foreground running function
run_in_foreground() {
    START_TIME=$(date +"%Y-%m-%d %H:%M:%S")
    echo -e "${GREEN}[$START_TIME] Starting article crawler...${NC}" | tee -a "$RUNTIME_LOG"
    echo -e "${YELLOW}Press Ctrl+C to stop${NC}"
    
    # Run the crawler and capture its PID
    python3 "$CRAWLER_SCRIPT" "$@" 2>&1 | tee -a "$RUNTIME_LOG" &
    CRAWLER_PID=$!
    
    # Save PID to file
    echo "$CRAWLER_PID" > "$PID_FILE"
    
    # Wait for process to complete
    wait $CRAWLER_PID
    EXIT_CODE=$?
    
    # Clean up PID file when done
    rm -f "$PID_FILE"
    
    END_TIME=$(date +"%Y-%m-%d %H:%M:%S")
    if [ $EXIT_CODE -eq 0 ]; then
        echo -e "${GREEN}[$END_TIME] Article extraction completed successfully. All categories processed.${NC}" | tee -a "$RUNTIME_LOG"
        return 0
    else
        echo -e "${RED}[$END_TIME] Article extraction failed with error code $EXIT_CODE${NC}" | tee -a "$RUNTIME_LOG"
        return $EXIT_CODE
    fi
}

# Run in appropriate mode
if [ "$BACKGROUND" = true ]; then
    run_in_background "$@"
    exit 0
else
    run_in_foreground "$@"
    exit $?
fi
