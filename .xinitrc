#!/bin/bash
# X initialization script for video player

# Disable screen blanking
xset s off 2>/dev/null
xset -dpms 2>/dev/null
xset s noblank 2>/dev/null

# Load video slicing configuration
. /home/pi/video_config.sh

# Start video player WITHOUT crop filter (videos are pre-processed on upload)
exec python3 /home/pi/video_player.py /home/pi/videos
