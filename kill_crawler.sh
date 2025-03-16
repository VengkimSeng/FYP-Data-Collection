#!/bin/bash

# Kill crawler process
echo "Terminating crawler process..."
if [ -f "crawler.pid" ]; then
  PID=$(cat "crawler.pid")
  kill $PID 2>/dev/null || kill -9 $PID 2>/dev/null
  rm "crawler.pid"
  echo "Crawler process terminated."
else
  echo "No crawler PID file found."
fi
