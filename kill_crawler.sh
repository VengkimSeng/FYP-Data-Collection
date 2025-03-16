#!/bin/bash
# Kill crawler process
echo "Terminating crawler process..."
if [ -f "/home/root/FYP-Data-Collection/FYP-Data-Collection/crawler.pid" ]; then
  PID=$(cat "/home/root/FYP-Data-Collection/FYP-Data-Collection/crawler.pid")
  kill $PID 2>/dev/null || kill -9 $PID 2>/dev/null
  rm "/home/root/FYP-Data-Collection/FYP-Data-Collection/crawler.pid"
  echo "Crawler process terminated."
else
  echo "No crawler PID file found."
fi
