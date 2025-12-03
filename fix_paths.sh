#!/bin/bash
# Fix path issues

echo "=========================================="
echo "Path Diagnostic and Fix"
echo "=========================================="
echo ""

echo "1. Check folder existence:"
echo "-----------------------------------"
if [ -d "/home/pi/videos" ]; then
    echo "✓ /home/pi/videos exists"
    ls -ld /home/pi/videos
else
    echo "✗ /home/pi/videos does NOT exist"
    echo "Creating it..."
    mkdir -p /home/pi/videos
fi
echo ""

if [ -d "/home/pi/videos/uploads" ]; then
    echo "✓ /home/pi/videos/uploads exists"
    ls -ld /home/pi/videos/uploads
else
    echo "✗ /home/pi/videos/uploads does NOT exist"
    echo "Creating it..."
    mkdir -p /home/pi/videos/uploads
fi
echo ""

echo "2. Check permissions:"
echo "-----------------------------------"
ls -la /home/pi/videos/
echo ""

echo "3. Check videos:"
echo "-----------------------------------"
echo "Processed videos:"
ls -lh /home/pi/videos/*.mp4 2>/dev/null || echo "  No .mp4 files"
echo ""
echo "Raw uploads:"
ls -lh /home/pi/videos/uploads/*.mp4 2>/dev/null || echo "  No .mp4 files"
echo ""

echo "4. Test if video_player.py can access the folder:"
echo "-----------------------------------"
python3 -c "
from pathlib import Path
folder = Path('/home/pi/videos')
print(f'Exists: {folder.exists()}')
print(f'Is dir: {folder.is_dir()}')
print(f'Absolute: {folder.resolve()}')
try:
    files = list(folder.iterdir())
    print(f'Files: {len(files)}')
    for f in files:
        print(f'  - {f.name}')
except Exception as e:
    print(f'Error: {e}')
"
echo ""

echo "5. Check .xinitrc:"
echo "-----------------------------------"
cat ~/.xinitrc | grep "video_player.py"
echo ""

echo "=========================================="
echo "If folder exists but service can't see it,"
echo "the issue might be with systemd user context."
echo "=========================================="
