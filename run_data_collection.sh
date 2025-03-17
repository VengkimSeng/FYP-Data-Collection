#!/bin/bash

# Data Collection Script Launcher
# This script launches the Data Collection CLI and ensures all dependencies are in place

# Set the script to exit on error
set -e

# Define colors
GREEN='\033[0;32m'
YELLOW='\033[0;33m'
RED='\033[0;31m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Define the project root
PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$PROJECT_ROOT"

echo -e "${BLUE}=== Khmer News Data Collection Tool ===${NC}"
echo -e "${GREEN}Initializing...${NC}"

# Check if virtual environment exists, create if not
if [ ! -d "venv" ]; then
    echo -e "${YELLOW}Virtual environment not found, creating...${NC}"
    python3 -m venv venv
    # Activate virtual environment
    source venv/bin/activate
    # Install requirements
    echo -e "${GREEN}Installing dependencies...${NC}"
    pip install -r requirements.txt
else
    # Activate virtual environment
    source venv/bin/activate
fi

# Create necessary directories
echo -e "${GREEN}Ensuring directories exist...${NC}"
mkdir -p config
mkdir -p output/urls
mkdir -p output/articles
mkdir -p output/test_reports
mkdir -p logs

# Run the main CLI script
echo -e "${BLUE}Starting Data Collection tool...${NC}"
python3 Data_Collection_CLI.py "$@"

# Deactivate virtual environment when done
deactivate
