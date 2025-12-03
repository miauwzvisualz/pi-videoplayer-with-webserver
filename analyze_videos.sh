#!/bin/bash
# Video Analysis Script for Raspberry Pi
# Analyzes all videos in the folder and identifies potential playback issues

VIDEO_DIR="${1:-/home/pi/videos}"
OUTPUT_FILE="/tmp/video_analysis.txt"

echo "========================================"
echo "Video Analysis for Raspberry Pi"
echo "========================================"
echo "Analyzing videos in: $VIDEO_DIR"
echo "Output will be saved to: $OUTPUT_FILE"
echo ""

# Clear output file
> "$OUTPUT_FILE"

# Check if directory exists
if [ ! -d "$VIDEO_DIR" ]; then
    echo "ERROR: Directory $VIDEO_DIR does not exist"
    exit 1
fi

# Count videos
video_count=$(find "$VIDEO_DIR" -type f \( -iname "*.mp4" -o -iname "*.avi" -o -iname "*.mkv" -o -iname "*.mov" -o -iname "*.webm" \) | wc -l)
echo "Found $video_count video file(s)"
echo ""

# Function to analyze a single video
analyze_video() {
    local video="$1"
    local filename=$(basename "$video")
    
    echo "----------------------------------------" | tee -a "$OUTPUT_FILE"
    echo "File: $filename" | tee -a "$OUTPUT_FILE"
    echo "----------------------------------------" | tee -a "$OUTPUT_FILE"
    
    # Get file size
    size=$(du -h "$video" | cut -f1)
    echo "Size: $size" | tee -a "$OUTPUT_FILE"
    
    # Get video properties using ffprobe
    if command -v ffprobe &> /dev/null; then
        # Get codec info
        codec=$(ffprobe -v error -select_streams v:0 -show_entries stream=codec_name -of default=noprint_wrappers=1:nokey=1 "$video" 2>/dev/null)
        width=$(ffprobe -v error -select_streams v:0 -show_entries stream=width -of default=noprint_wrappers=1:nokey=1 "$video" 2>/dev/null)
        height=$(ffprobe -v error -select_streams v:0 -show_entries stream=height -of default=noprint_wrappers=1:nokey=1 "$video" 2>/dev/null)
        fps=$(ffprobe -v error -select_streams v:0 -show_entries stream=r_frame_rate -of default=noprint_wrappers=1:nokey=1 "$video" 2>/dev/null)
        bitrate=$(ffprobe -v error -select_streams v:0 -show_entries stream=bit_rate -of default=noprint_wrappers=1:nokey=1 "$video" 2>/dev/null)
        duration=$(ffprobe -v error -show_entries format=duration -of default=noprint_wrappers=1:nokey=1 "$video" 2>/dev/null)
        profile=$(ffprobe -v error -select_streams v:0 -show_entries stream=profile -of default=noprint_wrappers=1:nokey=1 "$video" 2>/dev/null)
        
        echo "Codec: $codec" | tee -a "$OUTPUT_FILE"
        echo "Resolution: ${width}x${height}" | tee -a "$OUTPUT_FILE"
        echo "Frame Rate: $fps" | tee -a "$OUTPUT_FILE"
        echo "Profile: $profile" | tee -a "$OUTPUT_FILE"
        
        # Convert bitrate to Mbps if available
        if [ -n "$bitrate" ] && [ "$bitrate" != "N/A" ]; then
            bitrate_mbps=$(echo "scale=2; $bitrate / 1000000" | bc)
            echo "Bitrate: ${bitrate_mbps} Mbps" | tee -a "$OUTPUT_FILE"
        else
            echo "Bitrate: Unknown" | tee -a "$OUTPUT_FILE"
        fi
        
        # Convert duration to readable format
        if [ -n "$duration" ]; then
            duration_formatted=$(printf '%02d:%02d:%02d\n' $((${duration%.*}/3600)) $((${duration%.*}%3600/60)) $((${duration%.*}%60)))
            echo "Duration: $duration_formatted" | tee -a "$OUTPUT_FILE"
        fi
        
        # Check for potential issues
        echo "" | tee -a "$OUTPUT_FILE"
        echo "Potential Issues:" | tee -a "$OUTPUT_FILE"
        
        issues_found=0
        
        # Check codec
        if [ "$codec" = "hevc" ] || [ "$codec" = "h265" ]; then
            echo "  ⚠️  H.265/HEVC codec - Limited hardware support on Pi" | tee -a "$OUTPUT_FILE"
            issues_found=1
        fi
        
        # Check bitrate
        if [ -n "$bitrate" ] && [ "$bitrate" != "N/A" ]; then
            if [ "$bitrate" -gt 10000000 ]; then
                echo "  ⚠️  High bitrate (>10 Mbps) - May cause stuttering" | tee -a "$OUTPUT_FILE"
                issues_found=1
            fi
        fi
        
        # Check resolution
        if [ -n "$width" ] && [ "$width" -gt 1920 ]; then
            echo "  ⚠️  High resolution (>1080p) - May strain CPU" | tee -a "$OUTPUT_FILE"
            issues_found=1
        fi
        
        # Check for variable frame rate
        if [[ "$fps" == *"/"* ]]; then
            numerator=$(echo "$fps" | cut -d'/' -f1)
            denominator=$(echo "$fps" | cut -d'/' -f2)
            if [ "$denominator" != "1" ] && [ "$denominator" != "1000" ] && [ "$denominator" != "1001" ]; then
                echo "  ⚠️  Unusual frame rate - May cause sync issues" | tee -a "$OUTPUT_FILE"
                issues_found=1
            fi
        fi
        
        if [ $issues_found -eq 0 ]; then
            echo "  ✅ No obvious issues detected" | tee -a "$OUTPUT_FILE"
        fi
        
    else
        echo "ERROR: ffprobe not found. Install ffmpeg to analyze videos." | tee -a "$OUTPUT_FILE"
    fi
    
    echo "" | tee -a "$OUTPUT_FILE"
}

# Analyze all videos
find "$VIDEO_DIR" -type f \( -iname "*.mp4" -o -iname "*.avi" -o -iname "*.mkv" -o -iname "*.mov" -o -iname "*.webm" \) | while read -r video; do
    analyze_video "$video"
done

# Summary
echo "========================================"
echo "Analysis complete!"
echo "Full report saved to: $OUTPUT_FILE"
echo ""
echo "System Information:"
echo "========================================"

# Check CPU temperature
if command -v vcgencmd &> /dev/null; then
    temp=$(vcgencmd measure_temp)
    echo "CPU Temperature: $temp"
    
    # Check throttling
    throttled=$(vcgencmd get_throttled)
    echo "Throttle Status: $throttled"
    if [ "$throttled" != "throttled=0x0" ]; then
        echo "  ⚠️  WARNING: Throttling detected! Pi may be overheating or underpowered."
    fi
fi

# Check available memory
echo ""
echo "Memory Usage:"
free -h

# Check for hardware acceleration support
echo ""
echo "Hardware Acceleration:"
if command -v ffmpeg &> /dev/null; then
    echo "Available hardware accelerators:"
    ffmpeg -hwaccels 2>/dev/null | grep -v "Hardware acceleration" | grep -v "^$"
fi

echo ""
echo "========================================"
echo "Recommendations:"
echo "========================================"
echo "1. Check $OUTPUT_FILE for videos with warnings"
echo "2. Re-encode problematic videos with:"
echo "   ffmpeg -i input.mp4 -c:v libx264 -crf 23 -maxrate 5M -bufsize 10M -c:a aac output.mp4"
echo "3. Monitor logs with: tail -f /tmp/video_player.log"
echo "4. Check system temperature regularly"
echo ""
