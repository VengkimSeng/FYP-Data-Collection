#!/usr/bin/env python3
"""
Script to stop the article crawler by creating a shutdown signal file.
"""

import os
import sys
import time
import signal
from colorama import Fore, Style, init

init(autoreset=True)

def find_crawler_pid():
    """Try to find the PID of the running crawler process."""
    try:
        import psutil
        for proc in psutil.process_iter(['pid', 'name', 'cmdline']):
            try:
                cmdline = proc.cmdline()
                if any('main.py' in cmd for cmd in cmdline) and any('extractors' in cmd for cmd in cmdline):
                    return proc.pid
            except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
                pass
        return None
    except ImportError:
        print(f"{Fore.YELLOW}psutil module not available, can't automatically find crawler PID{Style.RESET_ALL}")
        return None

def main():
    """Main function to stop the crawler."""
    print(f"{Fore.CYAN}Article Crawler Terminator{Style.RESET_ALL}")
    print(f"{Fore.CYAN}========================={Style.RESET_ALL}")
    
    # Try to find crawler PID
    pid = find_crawler_pid()
    if pid:
        print(f"{Fore.GREEN}Found crawler process with PID: {pid}{Style.RESET_ALL}")
        
        # First try to create the signal file for a graceful shutdown
        print(f"{Fore.YELLOW}Creating shutdown signal file...{Style.RESET_ALL}")
        try:
            with open("shutdown.signal", "w") as f:
                f.write(f"Shutdown requested at {time.strftime('%Y-%m-%d %H:%M:%S')}")
            print(f"{Fore.GREEN}Shutdown signal file created. Waiting for crawler to shut down...{Style.RESET_ALL}")
            
            # Wait for up to 30 seconds for the process to terminate
            import psutil
            proc = psutil.Process(pid)
            for _ in range(30):
                if not proc.is_running():
                    print(f"{Fore.GREEN}Crawler has shut down gracefully.{Style.RESET_ALL}")
                    break
                time.sleep(1)
            else:
                # Process still running, send SIGTERM
                print(f"{Fore.YELLOW}Crawler still running after 30 seconds, sending SIGTERM...{Style.RESET_ALL}")
                try:
                    os.kill(pid, signal.SIGTERM)
                    print(f"{Fore.GREEN}SIGTERM sent to process {pid}.{Style.RESET_ALL}")
                except Exception as e:
                    print(f"{Fore.RED}Failed to send SIGTERM: {e}{Style.RESET_ALL}")
        except Exception as e:
            print(f"{Fore.RED}Error creating shutdown file: {e}{Style.RESET_ALL}")
            
            # Try direct termination instead
            try:
                os.kill(pid, signal.SIGTERM)
                print(f"{Fore.GREEN}SIGTERM sent to process {pid}.{Style.RESET_ALL}")
            except Exception as e:
                print(f"{Fore.RED}Failed to send SIGTERM: {e}{Style.RESET_ALL}")
    else:
        print(f"{Fore.YELLOW}No crawler process found. Creating shutdown signal file anyway...{Style.RESET_ALL}")
        try:
            with open("shutdown.signal", "w") as f:
                f.write(f"Shutdown requested at {time.strftime('%Y-%m-%d %H:%M:%S')}")
            print(f"{Fore.GREEN}Shutdown signal file created.{Style.RESET_ALL}")
        except Exception as e:
            print(f"{Fore.RED}Error creating shutdown file: {e}{Style.RESET_ALL}")
    
    print(f"{Fore.CYAN}If the crawler is still running, you can try these commands:{Style.RESET_ALL}")
    if pid:
        print(f"  kill {pid}            # Send termination signal")
        print(f"  kill -9 {pid}         # Force kill if still running")
    else:
        print("  ps aux | grep python   # Find the crawler process")
        print("  kill <PID>             # Send termination signal to the crawler process")
    
    return 0

if __name__ == "__main__":
    sys.exit(main())
