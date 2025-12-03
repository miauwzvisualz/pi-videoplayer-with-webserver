#!/bin/bash
# Setup script for video pre-processing system
# Run this on the Raspberry Pi after uploading the files

echo "=========================================="
echo "Video Pre-Processing Setup"
echo "=========================================="
echo ""

# Create folder structure
echo "1. Creating folder structure..."
mkdir -p /home/pi/videos/uploads
echo "   ✓ Created /home/pi/videos/uploads (raw uploads)"
echo "   ✓ /home/pi/videos (processed videos for playback)"
echo ""

# Move existing videos to uploads folder
echo "2. Moving existing videos to uploads folder..."
if ls /home/pi/videos/*.mp4 2>/dev/null | grep -v "processed_" >/dev/null; then
    mv /home/pi/videos/*.mp4 /home/pi/videos/uploads/ 2>/dev/null
    echo "   ✓ Moved .mp4 files"
fi
if ls /home/pi/videos/*.avi 2>/dev/null | grep -v "processed_" >/dev/null; then
    mv /home/pi/videos/*.avi /home/pi/videos/uploads/ 2>/dev/null
    echo "   ✓ Moved .avi files"
fi
if ls /home/pi/videos/*.mkv 2>/dev/null | grep -v "processed_" >/dev/null; then
    mv /home/pi/videos/*.mkv /home/pi/videos/uploads/ 2>/dev/null
    echo "   ✓ Moved .mkv files"
fi
echo ""

# Check if video player service is running
echo "3. Checking video player service..."
if systemctl is-active --quiet video-player-x11.service; then
    echo "   ✓ Service is running"
    echo "   → Restarting to apply new configuration..."
    sudo systemctl restart video-player-x11.service
    echo "   ✓ Service restarted"
else
    echo "   ⚠ Service is not running"
    echo "   → Starting service..."
    sudo systemctl start video-player-x11.service
    echo "   ✓ Service started"
fi
echo ""

# Check current videos
echo "4. Current video status:"
upload_count=$(find /home/pi/videos/uploads -type f \( -name "*.mp4" -o -name "*.avi" -o -name "*.mkv" \) 2>/dev/null | wc -l)
processed_count=$(find /home/pi/videos -maxdepth 1 -type f -name "processed_*" 2>/dev/null | wc -l)
echo "   Raw uploads: $upload_count files"
echo "   Processed videos: $processed_count files"
echo ""

if [ $upload_count -gt 0 ] && [ $processed_count -eq 0 ]; then
    echo "   ⚠ You have raw videos but no processed videos!"
    echo "   → Upload them via the web interface to process them"
    echo "   → Or process manually with:"
    echo "      cd /home/pi/videos/uploads"
    echo "      for video in *.mp4; do"
    echo "        ffmpeg -i \"\$video\" \\"
    echo "          -filter_complex '[0:v]crop=1792:64:0:0[top];[0:v]crop=1280:64:1792:0,pad=1792:64:0:0[bottom];[top][bottom]vstack,format=yuv420p' \\"
    echo "          -c:v libx264 -preset medium -crf 23 -maxrate 3M -bufsize 6M \\"
    echo "          -c:a copy \\"
    echo "          \"/home/pi/videos/processed_\$video\""
    echo "      done"
fi
echo ""

# Show log locations
echo "5. Log files:"
echo "   Video player: /tmp/video_player.log"
echo "   Upload server: /tmp/video_upload_server.log"
echo ""

# Show monitoring commands
echo "=========================================="
echo "Monitoring Commands:"
echo "=========================================="
echo "Video player logs:"
echo "  tail -f /tmp/video_player.log"
echo ""
echo "Upload server logs:"
echo "  tail -f /tmp/video_upload_server.log"
echo ""
echo "Video player service status:"
echo "  sudo systemctl status video-player-x11.service"
echo ""
echo "=========================================="
echo "Setup Complete!"
echo "=========================================="
echo ""
echo "Next steps:"
echo "1. Start upload server: python3 ~/video_upload_server.py"
echo "2. Upload videos via web interface: http://$(hostname -I | awk '{print $1}'):5000"
echo "3. Monitor logs to see processing progress"
echo ""
