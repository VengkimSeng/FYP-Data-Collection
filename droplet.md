# Running the Data Collection System on a DigitalOcean Droplet

This document outlines the step-by-step process to set up and run the Khmer News Data Collection system on a DigitalOcean droplet. This allows you to collect data continuously in the cloud without keeping your local machine running.

## Table of Contents

- [Creating a Droplet](#creating-a-droplet)
- [Initial Server Setup](#initial-server-setup)
- [Installing Dependencies](#installing-dependencies)
- [Cloning the Repository](#cloning-the-repository)
- [Running with Screen](#running-with-screen)
- [Monitoring and Maintenance](#monitoring-and-maintenance)
- [Common Issues and Solutions](#common-issues-and-solutions)

## Creating a Droplet

1. **Sign up/Log in to DigitalOcean**:

   - Create an account at [digitalocean.com](https://www.digitalocean.com/) if you don't have one
   - Log in to your account

2. **Create a new Droplet**:

   - Click on "Create" and select "Droplets"
   - Choose an image: **Ubuntu 22.04 LTS**
   - Select a plan:
     - Basic plan
     - Regular Intel CPU (not dedicated)
     - At least 2GB RAM / 1 CPU ($12/month recommended)
     - 50GB SSD disk or more
   - Choose a datacenter region (Singapore or another Asian region for better performance)
   - Authentication: SSH key (recommended) or password
   - Click "Create Droplet"

3. **Connect to Your Droplet**:
   ```bash
   ssh root@your_droplet_ip
   ```

## Initial Server Setup

1. **Update the system**:

   ```bash
   apt update && apt upgrade -y
   ```

2. **Create a new user** (optional but recommended):

   ```bash
   adduser username
   usermod -aG sudo username
   # Switch to the new user
   su - username
   ```

3. **Set up the firewall**:
   ```bash
   sudo ufw allow OpenSSH
   sudo ufw enable
   ```

## Installing Dependencies

1. **Install Python and required tools**:

   ```bash
   sudo apt install -y python3 python3-pip python3-venv git wget unzip
   ```

2. **Install Chrome and ChromeDriver**:

   ```bash
   # Install Chrome
   wget https://dl.google.com/linux/direct/google-chrome-stable_current_amd64.deb
   sudo apt install -y ./google-chrome-stable_current_amd64.deb

   # Install ChromeDriver
   CHROME_VERSION=$(google-chrome --version | awk '{print $3}' | cut -d. -f1)
   CHROMEDRIVER_VERSION=$(wget -qO- "https://chromedriver.storage.googleapis.com/LATEST_RELEASE_$CHROME_VERSION")
   wget "https://chromedriver.storage.googleapis.com/${CHROMEDRIVER_VERSION}/chromedriver_linux64.zip"
   unzip chromedriver_linux64.zip
   sudo mv chromedriver /usr/local/bin/
   sudo chmod +x /usr/local/bin/chromedriver
   ```

3. **Install screen for persistent sessions**:
   ```bash
   sudo apt install -y screen
   ```

## Cloning the Repository

1. **Clone the repository**:

   ```bash
   git clone https://github.com/yourusername/FYP-Data-Collection.git
   cd FYP-Data-Collection
   ```

2. **Set up Python environment**:

   ```bash
   python3 -m venv venv
   source venv/bin/activate
   pip install -r requirements.txt
   ```

3. **Create necessary directories**:

   ```bash
   mkdir -p output/logs output/urls config
   ```

4. **Configure the data collection system**:
   - Copy your configuration files to the `config` directory:
   ```bash
   # If you have local config files to upload:
   # Use SCP from your local machine
   scp config/categories.json username@your_droplet_ip:~/FYP-Data-Collection/config/
   scp config/sources.json username@your_droplet_ip:~/FYP-Data-Collection/config/
   ```

## Running with Screen

Screen allows you to run the data collection system in the background, even after you disconnect from the server.

1. **Make the bash script executable**:

   ```bash
   chmod +x run_data_collection.sh
   ```

2. **Start a new screen session**:

   ```bash
   screen -S data-collection
   ```

3. **Run the data collection system**:

   ```bash
   ./run_data_collection.sh
   ```

4. **Detach from the screen session**:
   Press `Ctrl+A` followed by `D` to detach from the screen session. The process will continue running in the background.

## Monitoring and Maintenance

1. **Reconnect to a running screen session**:

   ```bash
   screen -r data-collection
   ```

2. **View all screen sessions**:

   ```bash
   screen -ls
   ```

3. **Check the logs**:

   ```bash
   # View the latest logs
   tail -f output/logs/master_crawler_controller.log

   # View logs for a specific crawler
   tail -f output/logs/crawlers/btv.log
   ```

4. **Monitor disk usage**:

   ```bash
   df -h
   ```

5. **Monitor memory usage**:

   ```bash
   free -h
   ```

6. **Set up automatic backups** (optional):

   ```bash
   # Create a backup script
   cat > backup.sh << 'EOF'
   #!/bin/bash
   TIMESTAMP=$(date +"%Y%m%d_%H%M%S")
   BACKUP_DIR="backups"
   mkdir -p $BACKUP_DIR

   # Compress output directory
   tar -czf "$BACKUP_DIR/output_$TIMESTAMP.tar.gz" output/

   # Remove backups older than 7 days
   find $BACKUP_DIR -name "output_*.tar.gz" -mtime +7 -delete
   EOF

   # Make it executable
   chmod +x backup.sh

   # Add to crontab (runs daily at 2 AM)
   (crontab -l 2>/dev/null; echo "0 2 * * * $PWD/backup.sh") | crontab -
   ```

## Common Issues and Solutions

### Chrome crashes or doesn't start

If Chrome crashes or fails to start, this is often due to missing dependencies or insufficient memory:

```bash
# Install additional dependencies
sudo apt install -y libx11-xcb1 libxcomposite1 libxcursor1 libxdamage1 \
     libxi-dev libxtst-dev libnss3 libcups2 libxss1 libxrandr2 \
     libasound2 libatk1.0-0 libatk-bridge2.0-0 libpangocairo-1.0-0 \
     libgtk-3-0 libgbm1 libxshmfence1

# Run Chrome in no-sandbox mode (add this to your ChromeDriver options if needed)
# In chrome_setup.py, add the argument '--no-sandbox'
```

### Server out of memory

If the server runs out of memory, you might need to:

1. **Create a swap file**:

   ```bash
   # Create a 2GB swap file
   sudo fallocate -l 2G /swapfile
   sudo chmod 600 /swapfile
   sudo mkswap /swapfile
   sudo swapon /swapfile

   # Make swap permanent
   echo '/swapfile none swap sw 0 0' | sudo tee -a /etc/fstab
   ```

2. **Optimize crawler settings**:
   - Reduce the number of concurrent crawlers
   - Lower the number of URLs collected per category
   - Configure settings in the CLI interface

### Handling timeouts and connection issues

For more robust crawling on a remote server with potential connection issues:

1. **Adjust timeout settings** in `chrome_setup.py`
2. **Implement more retries** in crawler logic
3. **Configure proxies** if websites block your server's IP

### Automatic restart on crash

Add a wrapper script to automatically restart the system if it crashes:

```bash
cat > start_and_monitor.sh << 'EOF'
#!/bin/bash
while true; do
  echo "Starting data collection system..."
  ./run_data_collection.sh
  echo "Process ended with exit code $?. Restarting in 60 seconds..."
  sleep 60
done
EOF

chmod +x start_and_monitor.sh
```

Then run this script in your screen session instead of `run_data_collection.sh` directly.

## Advanced Setup

### Running as a systemd service

For more robust operation, you can set up the crawler as a systemd service:

1. **Create a service file**:

   ```bash
   sudo nano /etc/systemd/system/data-collector.service
   ```

2. **Add the following content**:

   ```
   [Unit]
   Description=Khmer News Data Collection System
   After=network.target

   [Service]
   Type=simple
   User=username
   WorkingDirectory=/home/username/FYP-Data-Collection
   ExecStart=/home/username/FYP-Data-Collection/run_data_collection.sh
   Restart=always
   RestartSec=60

   [Install]
   WantedBy=multi-user.target
   ```

3. **Enable and start the service**:

   ```bash
   sudo systemctl daemon-reload
   sudo systemctl enable data-collector
   sudo systemctl start data-collector
   ```

4. **Check status and logs**:
   ```bash
   sudo systemctl status data-collector
   sudo journalctl -u data-collector -f
   ```
