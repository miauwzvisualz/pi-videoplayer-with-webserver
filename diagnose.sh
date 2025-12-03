#!/bin/bash
# Diagnostic script to check video player status

echo "=========================================="
echo "Video Player Diagnostic"
echo "=========================================="
echo ""

echo "1. Current .xinitrc configuration:"
echo "-----------------------------------"
cat ~/.xinitrc
echo ""

echo "2. Videos in /home/pi/videos/:"
echo "-----------------------------------"
ls -lh /home/pi/videos/*.mp4 2>/dev/null || echo "No .mp4 files found"
ls -lh /home/pi/videos/*.avi 2>/dev/null || echo "No .avi files found"
ls -lh /home/pi/videos/*.mkv 2>/dev/null || echo "No .mkv files found"
echo ""

echo "3. Videos in /home/pi/videos/uploads/:"
echo "-----------------------------------"
ls -lh /home/pi/videos/uploads/*.mp4 2>/dev/null || echo "No .mp4 files found"
echo ""

echo "4. Video player process:"
echo "-----------------------------------"
ps aux | grep video_player | grep -v grep || echo "No video player process found"
echo ""

echo "5. Last 30 lines of video player log:"
echo "-----------------------------------"
tail -30 /tmp/video_player.log
echo ""

echo "6. Video player service status:"
echo "-----------------------------------"
systemctl status video-player-x11.service --no-pager
echo ""

echo "=========================================="
echo "Diagnostic complete!"
echo "=========================================="
