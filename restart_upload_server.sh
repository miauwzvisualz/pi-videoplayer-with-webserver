#!/bin/bash
# Restart the video upload server

echo "Restarting video upload server..."

# Find and kill existing server process
PID=$(pgrep -f "python3.*video_upload_server.py")

if [ -n "$PID" ]; then
    echo "Found running server (PID: $PID)"
    kill $PID
    sleep 2
    
    # Force kill if still running
    if ps -p $PID > /dev/null 2>&1; then
        echo "Force killing server..."
        kill -9 $PID
    fi
    echo "✓ Server stopped"
else
    echo "No running server found"
fi

echo ""
echo "Starting server with logging..."
echo "Logs will be written to: /tmp/video_upload_server.log"
echo ""
echo "Press Ctrl+C to stop the server"
echo "=========================================="
echo ""

# Start the server
cd /home/pi
python3 video_upload_server.py
