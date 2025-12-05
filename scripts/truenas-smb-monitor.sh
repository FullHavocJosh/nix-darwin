#!/usr/bin/env bash
#
# TrueNAS SCALE SMB Service Monitor
# This script checks if the SMB service is running and restarts it if needed
# Designed to run via cron to handle services that fail to start on boot

LOG_FILE="/var/log/smb-monitor.log"
MAX_LOG_SIZE=1048576  # 1MB in bytes

# Function to rotate log if it gets too large
rotate_log() {
    if [ -f "$LOG_FILE" ] && [ $(stat -f%z "$LOG_FILE" 2>/dev/null || stat -c%s "$LOG_FILE" 2>/dev/null) -gt $MAX_LOG_SIZE ]; then
        mv "$LOG_FILE" "${LOG_FILE}.old"
        echo "$(date '+%Y-%m-%d %H:%M:%S') - Log rotated" > "$LOG_FILE"
    fi
}

# Function to log messages
log_message() {
    echo "$(date '+%Y-%m-%d %H:%M:%S') - $1" >> "$LOG_FILE"
}

# Rotate log if needed
rotate_log

# Check if SMB service is running using TrueNAS CLI
SMB_STATUS=$(midclt call service.query '[["service", "=", "cifs"]]' | grep -o '"state":"[^"]*"' | cut -d'"' -f4)

if [ "$SMB_STATUS" != "RUNNING" ]; then
    log_message "SMB service is not running (status: $SMB_STATUS). Attempting to start..."
    
    # Try to start the SMB service using TrueNAS middleware
    if midclt call service.start cifs; then
        log_message "SMB service started successfully"
        
        # Wait a moment and verify it's running
        sleep 2
        VERIFY_STATUS=$(midclt call service.query '[["service", "=", "cifs"]]' | grep -o '"state":"[^"]*"' | cut -d'"' -f4)
        
        if [ "$VERIFY_STATUS" = "RUNNING" ]; then
            log_message "Verified: SMB service is now running"
        else
            log_message "WARNING: SMB service start command succeeded but service is not running (status: $VERIFY_STATUS)"
        fi
    else
        log_message "ERROR: Failed to start SMB service"
        exit 1
    fi
else
    log_message "SMB service is running normally"
fi

exit 0
