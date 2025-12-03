#!/bin/bash
# Wrapper script to start video player with proper error handling

# Wait for X server to be ready
sleep 3

# Set up logging
LOG_FILE="/tmp/video_player_startup.log"
echo "========================================" >> "$LOG_FILE"
echo "Video Player Startup: $(date)" >> "$LOG_FILE"
echo "========================================" >> "$LOG_FILE"

# Ensure DISPLAY is set
if [ -z "$DISPLAY" ]; then
    export DISPLAY=:0
    echo "Set DISPLAY=:0" >> "$LOG_FILE"
else
    echo "DISPLAY already set to: $DISPLAY" >> "$LOG_FILE"
fi

# Wait for X server to be accessible
echo "Waiting for X server..." >> "$LOG_FILE"
for i in {1..10}; do
    if xset q &>/dev/null 2>&1 || DISPLAY=:0 xdpyinfo &>/dev/null 2>&1; then
        echo "X server is ready" >> "$LOG_FILE"
        break
    fi
    echo "Waiting for X server (attempt $i/10)..." >> "$LOG_FILE"
    sleep 1
done

# Check if folder exists
if [ ! -d "/home/pi/videos" ]; then
    echo "ERROR: /home/pi/videos does not exist!" >> "$LOG_FILE"
    echo "Creating folder..." >> "$LOG_FILE"
    mkdir -p /home/pi/videos
fi

# Log environment
echo "Environment:" >> "$LOG_FILE"
echo "  DISPLAY: $DISPLAY" >> "$LOG_FILE"
echo "  USER: $(whoami)" >> "$LOG_FILE"
echo "  PWD: $(pwd)" >> "$LOG_FILE"
echo "  HOME: $HOME" >> "$LOG_FILE"

# Log folder contents
echo "Folder contents:" >> "$LOG_FILE"
ls -la /home/pi/videos >> "$LOG_FILE" 2>&1

# Start the video player
echo "Starting video player..." >> "$LOG_FILE"
exec python3 /home/pi/video_player.py /home/pi/videos
