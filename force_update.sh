#!/bin/bash
# Force update and restart video player

echo "Stopping video player service..."
sudo systemctl stop video-player-x11.service
sleep 2

echo "Killing any remaining processes..."
pkill -9 -f video_player.py
pkill -9 -f ffplay
pkill -9 -f ffmpeg
sleep 1

echo "Clearing log file..."
> /tmp/video_player.log

echo "Starting video player service..."
sudo systemctl start video-player-x11.service
sleep 3

echo ""
echo "=========================================="
echo "Service restarted. Checking logs..."
echo "=========================================="
tail -50 /tmp/video_player.log

echo ""
echo "=========================================="
echo "If you see only 'Using ffplay as video player backend'"
echo "then run the player manually to see the error:"
echo "  python3 /home/pi/video_player.py /home/pi/videos"
echo "=========================================="
