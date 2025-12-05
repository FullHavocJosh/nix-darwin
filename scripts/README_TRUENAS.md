# TrueNAS SCALE SMB Service Monitor

This script monitors the SMB/CIFS service on TrueNAS SCALE and automatically restarts it if it's not running. This is useful for cases where the SMB service fails to start on boot but can be manually started without errors.

## Installation

### 1. Copy the script to TrueNAS SCALE

```bash
# SSH into your TrueNAS SCALE server
ssh root@your-truenas-ip

# Create scripts directory if it doesn't exist
mkdir -p /root/scripts

# Copy the script (you can use nano/vi or scp it from your local machine)
nano /root/scripts/truenas-smb-monitor.sh
# Paste the script content and save
```

### 2. Make the script executable

```bash
chmod +x /root/scripts/truenas-smb-monitor.sh
```

### 3. Test the script manually

```bash
# Run the script to make sure it works
/root/scripts/truenas-smb-monitor.sh

# Check the log file
cat /var/log/smb-monitor.log
```

### 4. Set up the cron job via TrueNAS UI

**Option A: Using TrueNAS Web UI (Recommended)**

1. Go to **System Settings** → **Advanced** → **Cron Jobs**
2. Click **Add**
3. Configure:
   - **Description**: SMB Service Monitor
   - **Command**: `/root/scripts/truenas-smb-monitor.sh`
   - **Run As User**: root
   - **Schedule**: Choose one of:
     - **Every 5 minutes**: `*/5 * * * *` (recommended for quick recovery)
     - **Every 2 minutes**: `*/2 * * * *` (more aggressive)
     - **Every 10 minutes**: `*/10 * * * *` (less frequent)
     - **At boot + every 5 minutes**: Create two jobs:
       - One with `@reboot` schedule
       - One with `*/5 * * * *` schedule
4. Enable **Enabled** checkbox
5. Click **Save**

**Option B: Using command line**

```bash
# Edit root's crontab
crontab -e

# Add one of these lines:
# Check every 5 minutes
*/5 * * * * /root/scripts/truenas-smb-monitor.sh

# OR check at boot and every 5 minutes
@reboot sleep 60 && /root/scripts/truenas-smb-monitor.sh
*/5 * * * * /root/scripts/truenas-smb-monitor.sh
```

## Monitoring

### Check if the cron job is running

```bash
# View the log file
tail -f /var/log/smb-monitor.log

# Check recent SMB service events
grep "SMB service" /var/log/smb-monitor.log | tail -20
```

### Check SMB service status manually

```bash
# Using TrueNAS middleware
midclt call service.query '[["service", "=", "cifs"]]'

# Using systemctl (alternative)
systemctl status smbd
```

## Recommended Schedule

For your specific issue (service not starting on boot), I recommend:

1. **At boot** (with 60-second delay to allow system to stabilize):

   ```
   @reboot sleep 60 && /root/scripts/truenas-smb-monitor.sh
   ```

2. **Every 5 minutes** (for ongoing monitoring):
   ```
   */5 * * * * /root/scripts/truenas-smb-monitor.sh
   ```

This ensures the service is checked shortly after boot and continues to be monitored.

## Troubleshooting

### Log file location

- Main log: `/var/log/smb-monitor.log`
- Old log (after rotation): `/var/log/smb-monitor.log.old`

### If the script doesn't work

1. Check script permissions:

   ```bash
   ls -la /root/scripts/truenas-smb-monitor.sh
   ```

2. Check if midclt is available:

   ```bash
   which midclt
   midclt call service.query '[["service", "=", "cifs"]]'
   ```

3. Check cron service is running:

   ```bash
   systemctl status cron
   ```

4. Check cron logs:
   ```bash
   grep CRON /var/log/syslog | tail -20
   ```

## Notes

- The script uses TrueNAS SCALE's `midclt` command to interact with the middleware
- Log files are automatically rotated when they exceed 1MB
- The script logs all actions with timestamps for troubleshooting
- Logs both successful checks and restart attempts

## Persistence Across Updates

**Important**: TrueNAS SCALE system updates may reset certain directories. To ensure persistence:

1. **Store the script in a dataset** instead of `/root/scripts`:

   ```bash
   # Example: store in a pool
   mkdir -p /mnt/your-pool/scripts
   cp /root/scripts/truenas-smb-monitor.sh /mnt/your-pool/scripts/
   chmod +x /mnt/your-pool/scripts/truenas-smb-monitor.sh
   ```

2. **Update the cron job** to point to the new location:

   ```
   */5 * * * * /mnt/your-pool/scripts/truenas-smb-monitor.sh
   ```

3. **Init/Config Scripts**: You can also add this to TrueNAS's Init/Shutdown Scripts for guaranteed execution at boot.
