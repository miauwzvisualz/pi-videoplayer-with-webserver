# Troubleshooting Video Freezing Issues

## Problem
Some video files freeze during playback on Raspberry Pi, but play fine on other machines with ffplay.

## Root Causes

### 1. **Hardware Limitations**
- **CPU Overload**: Raspberry Pi has limited CPU power for software video decoding
- **Memory Constraints**: Large videos or high bitrates can exhaust RAM
- **GPU Acceleration**: Not all codecs support hardware acceleration on Pi

### 2. **Codec/Format Issues**
- **H.265/HEVC**: Limited hardware support on older Pi models
- **High Bitrate**: Videos with bitrates >10 Mbps may struggle
- **Variable Frame Rate (VFR)**: Can cause sync issues
- **B-frames**: Complex frame structures increase CPU load

### 3. **System Resource Competition**
- Other services consuming CPU/memory
- Thermal throttling when Pi gets too hot
- SD card I/O bottlenecks

## Enhanced Logging (Now Implemented)

The updated `video_player.py` now includes:
- ✅ Full stderr capture from ffmpeg/ffplay
- ✅ Process monitoring every 30 seconds
- ✅ Video file size logging
- ✅ Exit code tracking
- ✅ Detailed error messages
- ✅ Log file at `/tmp/video_player.log`

## Diagnostic Steps

### 1. Check the Enhanced Logs
```bash
# View real-time logs
sudo journalctl -u video-player-x11.service -f

# View the detailed log file
tail -f /tmp/video_player.log

# Search for errors
grep -i "error\|warning\|died" /tmp/video_player.log
```

### 2. Analyze Problematic Videos
Run this command on the Pi to check video properties:
```bash
ffprobe -v error -show_entries stream=codec_name,codec_type,width,height,r_frame_rate,bit_rate,profile,level -of default=noprint_wrappers=1 /home/pi/videos/YOUR_VIDEO.mp4
```

Look for:
- **Codec**: H.265/HEVC is problematic on older Pi models
- **Bitrate**: >10 Mbps may cause issues
- **Resolution**: Higher than 1080p may struggle
- **Frame rate**: VFR (variable) can cause freezing

### 3. Test Individual Videos
```bash
# Stop the service
sudo systemctl stop video-player-x11.service

# Test a specific video with verbose output
ffplay -v verbose /home/pi/videos/problematic_video.mp4

# Or test with hardware acceleration
ffplay -vcodec h264_mmal /home/pi/videos/problematic_video.mp4
```

### 4. Check System Resources
```bash
# Monitor CPU, memory, and temperature while playing
htop

# Check temperature (should be <80°C)
vcgencmd measure_temp

# Check for throttling
vcgencmd get_throttled
# 0x0 = OK, anything else = throttling occurred
```

## Solutions

### Solution 1: Re-encode Problematic Videos
Convert videos to Pi-friendly format on your computer:

```bash
# Convert to H.264 with lower bitrate
ffmpeg -i input.mp4 -c:v libx264 -preset slow -crf 23 -maxrate 5M -bufsize 10M -c:a aac -b:a 128k output.mp4

# For 3072x64 LED strip videos
ffmpeg -i input.mp4 -c:v libx264 -preset slow -crf 23 -maxrate 3M -bufsize 6M -c:a aac -b:a 128k -s 3072x64 output.mp4
```

Parameters explained:
- `-crf 23`: Quality (18-28, lower = better quality)
- `-maxrate 5M`: Max bitrate 5 Mbps
- `-preset slow`: Better compression (use on PC, not Pi)

### Solution 2: Use Hardware Acceleration (Pi 4 and newer)
Modify the ffplay command in `video_player.py` to use hardware decoder:

```python
# In play_playlist_gapless method, change ffplay_cmd to:
ffplay_cmd = [
    'ffplay',
    '-vcodec', 'h264_mmal',  # Hardware decoder
    '-fs',
    '-noborder',
    '-left', '0',
    '-top', '0',
    '-autoexit',
    '-loglevel', 'error',
    '-'
]
```

### Solution 3: Reduce Concurrent Load
```bash
# Disable unnecessary services
sudo systemctl disable bluetooth
sudo systemctl disable wifi-powersave

# Increase GPU memory (edit /boot/config.txt)
gpu_mem=256

# Overclock (Pi 4 - use with caution)
over_voltage=2
arm_freq=1750
```

### Solution 4: Use VLC Instead of ffplay
VLC has better hardware acceleration support:

```bash
# Install VLC
sudo apt-get install vlc

# Run video player with VLC backend
python3 video_player.py /home/pi/videos --backend vlc
```

## Quick Fixes to Try

### Fix 1: Lower Buffer Size
Edit `video_player.py` line 278-286 to add buffer size limits:
```python
ffmpeg_proc = subprocess.Popen(
    ffmpeg_cmd + ['-bufsize', '2M'],  # Add buffer limit
    stdout=subprocess.PIPE,
    stderr=subprocess.PIPE,
    text=True,
    bufsize=1
)
```

### Fix 2: Add Probesize Limit
In `play_playlist_gapless`, add to ffmpeg_cmd:
```python
ffmpeg_cmd = [
    'ffmpeg',
    '-probesize', '10M',      # Limit probe size
    '-analyzeduration', '5M',  # Limit analysis time
    '-f', 'concat',
    '-safe', '0',
    '-i', concat_file
]
```

### Fix 3: Enable Cooling
```bash
# Check if fan is working (if you have one)
# Add to /boot/config.txt for automatic fan control:
dtoverlay=gpio-fan,gpiopin=14,temp=65000
```

## Identifying Specific Video Issues

### Check Codec Support
```bash
# List supported decoders
ffmpeg -decoders | grep h264
ffmpeg -decoders | grep hevc

# Test hardware decoder
ffmpeg -hwaccels
```

### Compare Working vs Freezing Videos
```bash
# Get detailed info
ffprobe -v quiet -print_format json -show_format -show_streams working_video.mp4 > working.json
ffprobe -v quiet -print_format json -show_format -show_streams freezing_video.mp4 > freezing.json

# Compare the files
diff working.json freezing.json
```

## Expected Log Output (After Update)

With the enhanced logging, you should now see:
```
2024-11-20 22:16:00 - INFO - Playing 3 video(s) in gapless mode
2024-11-20 22:16:00 - INFO -   1. video1.mp4 (45.2 MB)
2024-11-20 22:16:00 - INFO -   2. video2.mp4 (67.8 MB)
2024-11-20 22:16:00 - INFO - Using stream copy (no re-encoding)
2024-11-20 22:16:00 - INFO - Starting ffmpeg: ffmpeg -f concat -safe 0 -i /tmp/...
2024-11-20 22:16:00 - INFO - Starting ffplay: ffplay -fs -noborder -left 0 -top 0...
2024-11-20 22:16:00 - INFO - Playback started, monitoring processes...
2024-11-20 22:16:30 - INFO - Playback running... (ffmpeg: None, ffplay: None)
2024-11-20 22:17:00 - INFO - Playback running... (ffmpeg: None, ffplay: None)
```

If a video freezes, you'll see:
```
2024-11-20 22:17:15 - WARNING - ffmpeg: [matroska @ 0x...] Application provided invalid, non monotonically increasing dts to muxer
2024-11-20 22:17:20 - ERROR - ffmpeg process died unexpectedly
2024-11-20 22:17:20 - INFO - Playback ended - ffmpeg exit code: 1, ffplay exit code: -15
```

## Next Steps

1. **Deploy the updated code** to your Raspberry Pi
2. **Restart the service**: `sudo systemctl restart video-player-x11.service`
3. **Monitor the logs**: `tail -f /tmp/video_player.log`
4. **Identify which videos freeze** and check their properties with ffprobe
5. **Re-encode problematic videos** using the commands above

## Additional Resources

- [Raspberry Pi Video Acceleration](https://www.raspberrypi.com/documentation/computers/config_txt.html#video-options)
- [FFmpeg Hardware Acceleration](https://trac.ffmpeg.org/wiki/HWAccelIntro)
- [H.264 vs H.265 on Pi](https://forums.raspberrypi.com/viewtopic.php?t=199775)
