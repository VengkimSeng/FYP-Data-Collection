#!/bin/bash
# Run Data Collection CLI
#
# This script provides a convenient way to run the Data Collection CLI
# from any directory, ensuring correct environment setup.
#
# Usage:
#   ./run_data_collection.sh [options]
#
# Example:
#   ./run_data_collection.sh --urls-per-category 1000

# Exit on error
set -e

# Get the directory where this script is located
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
echo "Script directory: $SCRIPT_DIR"

# Change to project directory
cd "$SCRIPT_DIR"
echo "Working directory: $(pwd)"

# Check if Python is available
if ! command -v python3 &> /dev/null; then
    echo "Error: Python 3 is required but not found."
    echo "Please install Python 3 and try again."
    exit 1
fi

# Check Python version
PYTHON_VERSION=$(python3 -c 'import sys; print("{}.{}.{}".format(*sys.version_info[:3]))')
echo "Python version: $PYTHON_VERSION"

# Check if virtual environment exists and activate it if it does
VENV_DIR="venv"
if [ -d "$VENV_DIR" ] && [ -f "$VENV_DIR/bin/activate" ]; then
    echo "Activating virtual environment..."
    source "$VENV_DIR/bin/activate"
    USING_VENV=true
else
    echo "No virtual environment found. Using system Python."
    USING_VENV=false
fi

# Check for required Python packages
echo "Checking required packages..."
REQUIREMENTS_FILE="requirements.txt"

if [ -f "$REQUIREMENTS_FILE" ]; then
    if [ "$USING_VENV" = true ]; then
        # Check if pip install is needed
        if pip list --outdated | grep -q "Package"; then
            echo "Installing/updating required packages..."
            pip install -r "$REQUIREMENTS_FILE"
        fi
    else
        echo "Warning: Not running in virtual environment. Package dependencies not checked."
    fi
else
    echo "Warning: requirements.txt not found. Cannot verify dependencies."
fi

# Create necessary directories if they don't exist
echo "Ensuring required directories exist..."
mkdir -p output/logs
mkdir -p output/urls
mkdir -p config

# Check if config files exist
if [ ! -f "config/categories.json" ]; then
    echo "Warning: config/categories.json not found."
fi

if [ ! -f "config/sources.json" ]; then
    echo "Warning: config/sources.json not found."
fi

# Run the CLI with all arguments passed to this script
echo "Starting Data Collection CLI..."
exec python3 Data_Collection_CLI.py "$@"
