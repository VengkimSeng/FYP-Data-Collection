#!/bin/bash

# Crawler Status and Management Script
# This script allows you to check the status of running crawler processes,
# view logs, and manage them (start/stop/restart)

# Define colors for output
GREEN='\033[0;32m'
YELLOW='\033[0;33m'
RED='\033[0;31m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
NC='\033[0m' # No Color

# Define paths
PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
LOG_DIR="$PROJECT_ROOT/output/logs/Article"
RUNTIME_LOG="$LOG_DIR/runtime.log"
PID_FILE="$LOG_DIR/crawler.pid"
CRAWLER_SCRIPT="$PROJECT_ROOT/scripts/run_article_crawler.sh"

# Check if the crawler is running
check_running() {
    if [ -f "$PID_FILE" ]; then
        CRAWLER_PID=$(cat "$PID_FILE")
        if ps -p "$CRAWLER_PID" > /dev/null; then
            return 0  # Process is running
        else
            echo -e "${YELLOW}PID file exists but process is not running. Cleaning up...${NC}"
            rm -f "$PID_FILE"
            return 1  # Process is not running
        fi
    fi
    return 1  # Process is not running
}

# Show the crawler process details
show_process_details() {
    if check_running; then
        CRAWLER_PID=$(cat "$PID_FILE")
        echo -e "${GREEN}Crawler is running with PID: $CRAWLER_PID${NC}"
        
        # Get process information
        if command -v ps > /dev/null; then
            echo -e "${CYAN}Process details:${NC}"
            ps -f -p $CRAWLER_PID
            
            # Get memory usage
            if command -v pmap > /dev/null; then
                MEM_USAGE=$(pmap -x $CRAWLER_PID | tail -n 1 | awk '{ print $4 }')
                echo -e "${CYAN}Memory usage: ${MEM_USAGE}KB${NC}"
            fi
            
            # Get runtime
            if command -v ps > /dev/null; then
                START_TIME=$(ps -o lstart= -p $CRAWLER_PID)
                echo -e "${CYAN}Started at: $START_TIME${NC}"
                
                # Calculate runtime if possible
                if command -v date > /dev/null; then
                    START_SECONDS=$(date -d "$START_TIME" +%s 2>/dev/null) || START_SECONDS=0
                    if [ $START_SECONDS -ne 0 ]; then
                        NOW_SECONDS=$(date +%s)
                        RUNTIME=$((NOW_SECONDS - START_SECONDS))
                        DAYS=$((RUNTIME / 86400))
                        HOURS=$(( (RUNTIME % 86400) / 3600 ))
                        MINUTES=$(( (RUNTIME % 3600) / 60 ))
                        SECONDS=$((RUNTIME % 60))
                        echo -e "${CYAN}Runtime: ${DAYS}d ${HOURS}h ${MINUTES}m ${SECONDS}s${NC}"
                    fi
                fi
            fi
            
            # Show related Chrome processes
            echo -e "\n${CYAN}Related Chrome processes:${NC}"
            CHROME_PIDS=$(pgrep -f "chrome.*--headless" || echo "")
            if [ -n "$CHROME_PIDS" ]; then
                ps -o pid,ppid,%cpu,%mem,command -p $CHROME_PIDS | grep -v PID
                CHROME_COUNT=$(echo "$CHROME_PIDS" | wc -l)
                echo -e "${CYAN}Total Chrome instances: $CHROME_COUNT${NC}"
            else
                echo -e "${YELLOW}No headless Chrome processes found${NC}"
            fi
            
            # Show chromedriver processes
            echo -e "\n${CYAN}ChromeDriver processes:${NC}"
            CHROMEDRIVER_PIDS=$(pgrep -f "chromedriver" || echo "")
            if [ -n "$CHROMEDRIVER_PIDS" ]; then
                ps -o pid,ppid,%cpu,%mem,command -p $CHROMEDRIVER_PIDS | grep -v PID
                CHROMEDRIVER_COUNT=$(echo "$CHROMEDRIVER_PIDS" | wc -l)
                echo -e "${CYAN}Total ChromeDriver instances: $CHROMEDRIVER_COUNT${NC}"
            else
                echo -e "${YELLOW}No ChromeDriver processes found${NC}"
            fi
        else
            echo -e "${YELLOW}ps command not available, cannot show detailed process info${NC}"
        fi
        
        # Show log file status
        if [ -f "$RUNTIME_LOG" ]; then
            LOG_SIZE=$(du -h "$RUNTIME_LOG" | cut -f1)
            LAST_MODIFIED=$(stat -c "%y" "$RUNTIME_LOG" 2>/dev/null || stat -f "%Sm" "$RUNTIME_LOG" 2>/dev/null)
            echo -e "\n${CYAN}Runtime log:${NC}"
            echo -e "${CYAN}  Path: $RUNTIME_LOG${NC}"
            echo -e "${CYAN}  Size: $LOG_SIZE${NC}"
            echo -e "${CYAN}  Last modified: $LAST_MODIFIED${NC}"
            
            # Show recent log entries
            echo -e "\n${CYAN}Last 10 log entries:${NC}"
            tail -n 10 "$RUNTIME_LOG"
        else
            echo -e "\n${YELLOW}No runtime log found at $RUNTIME_LOG${NC}"
        fi
    else
        echo -e "${YELLOW}Crawler is not running${NC}"
        
        # Check if logs exist from previous runs
        if [ -f "$RUNTIME_LOG" ]; then
            LOG_SIZE=$(du -h "$RUNTIME_LOG" | cut -f1)
            LAST_MODIFIED=$(stat -c "%y" "$RUNTIME_LOG" 2>/dev/null || stat -f "%Sm" "$RUNTIME_LOG" 2>/dev/null)
            echo -e "\n${CYAN}Previous runtime log:${NC}"
            echo -e "${CYAN}  Path: $RUNTIME_LOG${NC}"
            echo -e "${CYAN}  Size: $LOG_SIZE${NC}"
            echo -e "${CYAN}  Last modified: $LAST_MODIFIED${NC}"
            
            echo -e "\n${CYAN}Last log entries from previous run:${NC}"
            tail -n 10 "$RUNTIME_LOG"
        fi
    fi
}

# Start the crawler
start_crawler() {
    if check_running; then
        echo -e "${YELLOW}Crawler is already running with PID: $(cat "$PID_FILE")${NC}"
        return 1
    else
        echo -e "${GREEN}Starting crawler in background...${NC}"
        $CRAWLER_SCRIPT --background "$@"
        sleep 2
        if check_running; then
            echo -e "${GREEN}Crawler started successfully with PID: $(cat "$PID_FILE")${NC}"
            return 0
        else
            echo -e "${RED}Failed to start crawler${NC}"
            return 1
        fi
    fi
}

# Stop the crawler
stop_crawler() {
    if check_running; then
        CRAWLER_PID=$(cat "$PID_FILE")
        echo -e "${YELLOW}Stopping crawler with PID: $CRAWLER_PID${NC}"
        kill $CRAWLER_PID 2>/dev/null
        
        # Wait for process to terminate
        for i in {1..5}; do
            sleep 1
            if ! ps -p $CRAWLER_PID > /dev/null; then
                echo -e "${GREEN}Crawler stopped successfully${NC}"
                rm -f "$PID_FILE"
                return 0
            fi
            echo -e "${YELLOW}Waiting for crawler to terminate ($i/5)...${NC}"
        done
        
        # Force kill if necessary
        echo -e "${RED}Crawler did not terminate gracefully. Forcing...${NC}"
        kill -9 $CRAWLER_PID 2>/dev/null
        sleep 1
        if ! ps -p $CRAWLER_PID > /dev/null; then
            echo -e "${GREEN}Crawler forcefully terminated${NC}"
            rm -f "$PID_FILE"
            return 0
        else
            echo -e "${RED}Failed to terminate crawler process${NC}"
            return 1
        fi
    else
        echo -e "${YELLOW}Crawler is not running${NC}"
        return 0
    fi
}

# Restart the crawler
restart_crawler() {
    echo -e "${BLUE}Restarting crawler...${NC}"
    stop_crawler
    sleep 2
    start_crawler "$@"
}

# Clean up stale Chrome and ChromeDriver processes
cleanup_processes() {
    echo -e "${BLUE}Cleaning up stale browser processes...${NC}"
    
    # Find and kill stale ChromeDriver processes
    CHROMEDRIVER_PIDS=$(pgrep -f "chromedriver" || echo "")
    if [ -n "$CHROMEDRIVER_PIDS" ]; then
        echo -e "${YELLOW}Found $(echo "$CHROMEDRIVER_PIDS" | wc -l) ChromeDriver processes${NC}"
        for pid in $CHROMEDRIVER_PIDS; do
            echo -e "${YELLOW}Killing ChromeDriver process: $pid${NC}"
            kill $pid 2>/dev/null || kill -9 $pid 2>/dev/null
        done
    else
        echo -e "${GREEN}No ChromeDriver processes found${NC}"
    fi
    
    # Find and kill stale headless Chrome processes
    CHROME_PIDS=$(pgrep -f "chrome.*--headless" || echo "")
    if [ -n "$CHROME_PIDS" ]; then
        echo -e "${YELLOW}Found $(echo "$CHROME_PIDS" | wc -l) headless Chrome processes${NC}"
        for pid in $CHROME_PIDS; do
            echo -e "${YELLOW}Killing Chrome process: $pid${NC}"
            kill $pid 2>/dev/null || kill -9 $pid 2>/dev/null
        done
    else
        echo -e "${GREEN}No headless Chrome processes found${NC}"
    fi
    
    echo -e "${GREEN}Cleanup complete${NC}"
}

# Show help
show_help() {
    echo -e "${BLUE}Crawler Status and Management Script${NC}"
    echo -e "${YELLOW}Usage: $0 [command] [options]${NC}"
    echo ""
    echo -e "${CYAN}Commands:${NC}"
    echo "  status      Show the status of the crawler process (default)"
    echo "  start       Start the crawler in background mode"
    echo "  stop        Stop the running crawler process"
    echo "  restart     Restart the crawler process"
    echo "  logs        Show the crawler logs (tail -f)"
    echo "  cleanup     Clean up stale browser processes"
    echo "  help        Show this help message"
    echo ""
    echo -e "${CYAN}Examples:${NC}"
    echo "  $0                  # Show status"
    echo "  $0 start            # Start crawler in background"
    echo "  $0 start --reset-checkpoint  # Start and reset checkpoint"
    echo "  $0 stop             # Stop crawler"
    echo "  $0 logs             # Show live logs"
    echo "  $0 cleanup          # Clean up stale processes"
}

# Main script execution
if [ $# -eq 0 ]; then
    # No arguments, show status by default
    show_process_details
else
    case "$1" in
        status)
            show_process_details
            ;;
        start)
            shift
            start_crawler "$@"
            ;;
        stop)
            stop_crawler
            ;;
        restart)
            shift
            restart_crawler "$@"
            ;;
        logs)
            if [ -f "$RUNTIME_LOG" ]; then
                echo -e "${GREEN}Showing live logs (press Ctrl+C to exit):${NC}"
                tail -f "$RUNTIME_LOG"
            else
                echo -e "${RED}No log file found at $RUNTIME_LOG${NC}"
            fi
            ;;
        cleanup)
            cleanup_processes
            ;;
        help)
            show_help
            ;;
        *)
            echo -e "${RED}Unknown command: $1${NC}"
            show_help
            exit 1
            ;;
    esac
fi

exit 0
