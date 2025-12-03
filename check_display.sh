#!/bin/bash
# Check X11 display status

echo "=========================================="
echo "X11 Display Check"
echo "=========================================="
echo ""

echo "1. DISPLAY variable:"
echo "   Current: $DISPLAY"
echo ""

echo "2. X server processes:"
ps aux | grep Xorg | grep -v grep
echo ""

echo "3. Check if X is accessible:"
if [ -n "$DISPLAY" ]; then
    xset q 2>&1 | head -5
else
    echo "   DISPLAY not set"
fi
echo ""

echo "4. Try setting DISPLAY and testing:"
export DISPLAY=:0
echo "   Set DISPLAY=:0"
xset q 2>&1 | head -5
echo ""

echo "=========================================="
echo "Now try running the player from the service:"
echo "  sudo systemctl restart video-player-x11.service"
echo "  sudo journalctl -u video-player-x11.service -f"
echo "=========================================="
