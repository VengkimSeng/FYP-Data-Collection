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

# Ensure required directories exist
mkdir -p "$LOG_DIR"
mkdir -p "$PROJECT_ROOT/output/urls"
mkdir -p "$PROJECT_ROOT/output/articles"
mkdir -p "$CHECKPOINT_DIR"

echo -e "${BLUE}=== Khmer News Article Crawler ===${NC}"
echo -e "${GREEN}Starting article extraction...${NC}"
echo -e "${YELLOW}Logs will be saved to: $RUNTIME_LOG${NC}"
echo -e "${YELLOW}Press Ctrl+C to stop${NC}"

# Check for ChromeDriver availability
check_chromedriver() {
    echo -e "${BLUE}Checking ChromeDriver availability...${NC}" | tee -a "$RUNTIME_LOG"
    
    if command -v chromedriver > /dev/null; then
        CHROMEDRIVER_VERSION=$(chromedriver --version | head -n 1)
        echo -e "${GREEN}✓ ChromeDriver found: $CHROMEDRIVER_VERSION${NC}" | tee -a "$RUNTIME_LOG"
    else
        echo -e "${YELLOW}⚠️ ChromeDriver not found in PATH${NC}" | tee -a "$RUNTIME_LOG"
        
        # Detect platform and suggest installation method
        if [[ "$OSTYPE" == "linux-gnu"* ]]; then
            echo -e "${YELLOW}On Ubuntu/Debian Linux, install ChromeDriver with:${NC}" | tee -a "$RUNTIME_LOG"
            echo -e "${YELLOW}  sudo apt update && sudo apt install -y chromium-chromedriver${NC}" | tee -a "$RUNTIME_LOG"
        elif [[ "$OSTYPE" == "darwin"* ]]; then
            echo -e "${YELLOW}On macOS, install ChromeDriver with:${NC}" | tee -a "$RUNTIME_LOG"
            echo -e "${YELLOW}  brew install --cask chromedriver${NC}" | tee -a "$RUNTIME_LOG"
        else
            echo -e "${YELLOW}Please download ChromeDriver from:${NC}" | tee -a "$RUNTIME_LOG"
            echo -e "${YELLOW}  https://chromedriver.chromium.org/downloads${NC}" | tee -a "$RUNTIME_LOG"
        fi
        
        echo -e "${YELLOW}The script will attempt to continue using selenium-manager...${NC}" | tee -a "$RUNTIME_LOG"
    fi
}

# Check for ChromeDriver before starting
check_chromedriver

# Run the crawler with all arguments passed to this script
START_TIME=$(date +"%Y-%m-%d %H:%M:%S")
echo -e "${GREEN}[$START_TIME] Starting article crawler...${NC}" | tee -a "$RUNTIME_LOG"

# Run the crawler
python3 "$CRAWLER_SCRIPT" "$@" 2>&1 | tee -a "$RUNTIME_LOG"

# Check if it was successful and exit with appropriate status
EXIT_CODE=$?
END_TIME=$(date +"%Y-%m-%d %H:%M:%S")

if [ $EXIT_CODE -eq 0 ]; then
    echo -e "${GREEN}[$END_TIME] Article extraction completed successfully. All categories processed.${NC}" | tee -a "$RUNTIME_LOG"
    exit 0
else
    echo -e "${RED}[$END_TIME] Article extraction failed with error code $EXIT_CODE${NC}" | tee -a "$RUNTIME_LOG"
    exit $EXIT_CODE
fi
