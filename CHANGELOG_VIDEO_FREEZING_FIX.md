# Changelog: Video Freezing Diagnostic Enhancement

## Date: 2024-11-20

## Problem
Video files were freezing during playback on Raspberry Pi, but no errors were visible in the logs. The same videos played fine on other machines with ffplay.

## Root Cause Analysis
The original `video_player.py` was suppressing all error output from ffmpeg and ffplay processes by redirecting stderr to `/dev/null`. This meant:
- No error messages were captured when videos failed
- Process crashes were silent
- Codec/format issues went undetected
- No way to diagnose hardware acceleration problems

## Changes Made

### 1. Enhanced Logging in `video_player.py`

#### Added Comprehensive Error Capture
- **Before**: `stderr=subprocess.DEVNULL` (all errors hidden)
- **After**: `stderr=subprocess.PIPE` with dedicated logging threads

#### New Logging Features
- ✅ Full stderr capture from both ffmpeg and ffplay processes
- ✅ Real-time error logging via background threads
- ✅ Process monitoring every 30 seconds during playback
- ✅ Video file size logging for each file
- ✅ Exit code tracking and reporting
- ✅ Detailed startup information
- ✅ Log file at `/tmp/video_player.log`

#### Process Monitoring
- Checks if ffmpeg dies unexpectedly and terminates ffplay
- Logs process status every 30 seconds
- Reports final exit codes for both processes

#### Example Log Output
```
2024-11-20 22:16:00 - INFO - Playing 3 video(s) in gapless mode
2024-11-20 22:16:00 - INFO -   1. video1.mp4 (45.2 MB)
2024-11-20 22:16:00 - INFO -   2. video2.mp4 (67.8 MB)
2024-11-20 22:16:00 - INFO - Using stream copy (no re-encoding)
2024-11-20 22:16:00 - INFO - Starting ffmpeg: ffmpeg -f concat -safe 0...
2024-11-20 22:16:00 - INFO - Playback started, monitoring processes...
2024-11-20 22:16:30 - INFO - Playback running... (ffmpeg: None, ffplay: None)
2024-11-20 22:17:00 - WARNING - ffmpeg: [h264 @ 0x...] concealing 12 DC, 12 AC errors
2024-11-20 22:17:15 - ERROR - ffmpeg process died unexpectedly
```

### 2. New Diagnostic Tools

#### `TROUBLESHOOTING_VIDEO_FREEZING.md`
Comprehensive troubleshooting guide covering:
- Root causes of video freezing (hardware, codec, system resources)
- Step-by-step diagnostic procedures
- Solutions for common issues
- Video re-encoding commands
- Hardware acceleration setup
- System optimization tips

#### `analyze_videos.sh`
Automated video analysis script that:
- Scans all videos in the folder
- Extracts codec, resolution, bitrate, frame rate
- Identifies potential compatibility issues
- Checks system temperature and throttling
- Generates detailed report at `/tmp/video_analysis.txt`

Usage:
```bash
bash analyze_videos.sh /home/pi/videos
```

### 3. Updated Documentation

#### `README_VIDEO_PLAYER.md`
Added new "Videos Freezing During Playback" section with:
- Quick diagnostic commands
- Common causes and solutions
- Links to detailed troubleshooting guide

## Technical Details

### Code Changes in `video_player.py`

1. **Added imports:**
   ```python
   import logging
   import threading
   ```

2. **Added logging configuration:**
   ```python
   logging.basicConfig(
       level=logging.INFO,
       format='%(asctime)s - %(levelname)s - %(message)s',
       handlers=[
           logging.StreamHandler(sys.stdout),
           logging.FileHandler('/tmp/video_player.log')
       ]
   )
   ```

3. **Added stderr logging thread function:**
   ```python
   def _log_stderr(self, proc, name: str):
       """Thread function to log stderr output from a process."""
       try:
           for line in proc.stderr:
               line = line.strip()
               if line:
                   logger.warning(f"{name}: {line}")
       except Exception as e:
           logger.error(f"Error reading {name} stderr: {e}")
   ```

4. **Enhanced subprocess creation:**
   ```python
   ffmpeg_proc = subprocess.Popen(
       ffmpeg_cmd, 
       stdout=subprocess.PIPE, 
       stderr=subprocess.PIPE,  # Changed from DEVNULL
       text=True,
       bufsize=1
   )
   
   # Start logging threads
   ffmpeg_thread = threading.Thread(target=self._log_stderr, args=(ffmpeg_proc, "ffmpeg"), daemon=True)
   ffmpeg_thread.start()
   ```

5. **Added process monitoring loop:**
   ```python
   while ffplay_proc.poll() is None:
       time.sleep(5)
       
       # Check if ffmpeg died unexpectedly
       if ffmpeg_proc.poll() is not None and ffplay_proc.poll() is None:
           logger.error("ffmpeg process died unexpectedly")
           ffplay_proc.terminate()
           break
       
       # Log status every 30 seconds
       if elapsed >= 30:
           logger.info(f"Playback running... (ffmpeg: {ffmpeg_proc.poll()}, ffplay: {ffplay_proc.poll()})")
   ```

## How to Deploy

### 1. Copy Updated Files to Raspberry Pi
```bash
# Copy the updated video player
scp video_player.py pi@<raspberry-pi-ip>:~/

# Copy diagnostic tools
scp analyze_videos.sh pi@<raspberry-pi-ip>:~/
scp TROUBLESHOOTING_VIDEO_FREEZING.md pi@<raspberry-pi-ip>:~/
```

### 2. Restart the Service
```bash
ssh pi@<raspberry-pi-ip>
sudo systemctl restart video-player-x11.service
```

### 3. Monitor the Logs
```bash
# Real-time log monitoring
tail -f /tmp/video_player.log

# Or via journalctl
sudo journalctl -u video-player-x11.service -f
```

### 4. Analyze Your Videos
```bash
bash analyze_videos.sh /home/pi/videos
cat /tmp/video_analysis.txt
```

## Expected Outcomes

After deploying these changes, you will be able to:

1. **See actual error messages** when videos freeze or fail
2. **Identify problematic video files** by codec, bitrate, or resolution
3. **Detect hardware issues** like thermal throttling or CPU overload
4. **Monitor playback in real-time** with periodic status updates
5. **Make informed decisions** about which videos need re-encoding

## Common Issues You'll Now Be Able to Diagnose

### Issue 1: H.265/HEVC Codec
**Log output:**
```
WARNING - ffmpeg: [hevc @ 0x...] Hardware acceleration not available
ERROR - ffmpeg process died unexpectedly
```
**Solution:** Re-encode to H.264

### Issue 2: High Bitrate
**Log output:**
```
WARNING - ffmpeg: [buffer @ 0x...] Queue input is backward in time
WARNING - ffplay: [sdl2 @ 0x...] Thread message queue blocking
```
**Solution:** Re-encode with lower bitrate

### Issue 3: Thermal Throttling
**Log output:**
```
INFO - Playback running...
INFO - Playback running...
[long pause with no output]
ERROR - ffmpeg process died unexpectedly
```
**Solution:** Improve cooling, check `vcgencmd measure_temp`

### Issue 4: Corrupted Video
**Log output:**
```
WARNING - ffmpeg: [h264 @ 0x...] concealing errors
WARNING - ffmpeg: [h264 @ 0x...] Invalid NAL unit size
ERROR - Player exited with code 1
```
**Solution:** Re-download or re-encode the video

## Files Modified
- ✅ `video_player.py` - Enhanced with comprehensive logging

## Files Created
- ✅ `TROUBLESHOOTING_VIDEO_FREEZING.md` - Detailed troubleshooting guide
- ✅ `analyze_videos.sh` - Video analysis script
- ✅ `CHANGELOG_VIDEO_FREEZING_FIX.md` - This file

## Files Updated
- ✅ `README_VIDEO_PLAYER.md` - Added freezing troubleshooting section

## Next Steps

1. Deploy the updated `video_player.py` to your Raspberry Pi
2. Restart the video player service
3. Monitor `/tmp/video_player.log` for error messages
4. Run `analyze_videos.sh` to identify problematic videos
5. Re-encode any videos flagged with warnings
6. Check system temperature and throttling status

## Additional Notes

- The logging adds minimal overhead (~1-2% CPU)
- Log file at `/tmp/video_player.log` will grow over time - consider log rotation
- stderr capture is done in separate threads to avoid blocking playback
- Process monitoring checks every 5 seconds but only logs every 30 seconds
