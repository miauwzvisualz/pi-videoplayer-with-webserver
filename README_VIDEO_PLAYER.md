# Video Player with FFmpeg Loop

A Python script that monitors a folder and plays all videos in a continuous loop on your display.

## Features

- **Automatic looping**: Plays all videos in a folder continuously
- **Multiple format support**: Supports MP4, AVI, MKV, MOV, WMV, FLV, WebM, M4V, MPG, MPEG
- **Auto-start on boot**: Runs automatically when your Raspberry Pi starts
- **Configurable delay**: Add delays between videos
- **Shuffle mode**: Randomize playback order
- **Easy controls**: Press 'Q' to skip to next video

## Current Setup

The video player is **already installed and running** on your system as a systemd service.

- **Video folder**: `/home/pi/videos/`
- **Service name**: `video-player-x11.service`
- **Auto-starts**: Yes, on every boot

## Managing the Video Player

### Stop the Player

```bash
sudo systemctl stop video-player-x11.service
```

### Start the Player

```bash
sudo systemctl start video-player-x11.service
```

### Restart the Player

```bash
sudo systemctl restart video-player-x11.service
```

### Check Status

```bash
sudo systemctl status video-player-x11.service
```

### View Logs

```bash
sudo journalctl -u video-player-x11.service -f
```

### Disable Auto-Start

```bash
sudo systemctl disable video-player-x11.service
```

### Enable Auto-Start

```bash
sudo systemctl enable video-player-x11.service
```

## Adding Videos

Simply copy video files to the videos folder:

```bash
cp /path/to/your/video.mp4 ~/videos/
```

The player will automatically include new videos in the next loop cycle.

## Manual Usage (Without Systemd)

If you want to run the player manually:

```bash
# Basic usage
python3 video_player.py ~/videos

# With 2-second delay between videos
python3 video_player.py ~/videos --delay 2

# Shuffle mode
python3 video_player.py ~/videos --shuffle

# Combined options
python3 video_player.py ~/videos --delay 1.5 --shuffle
```

## How It Works

1. The script scans the specified folder for video files
2. It plays each video using `ffplay` (part of ffmpeg)
3. After all videos are played, it loops back to the beginning
4. If no videos are found, it waits and checks again every 5 seconds

## Supported Video Formats

- .mp4, .avi, .mkv, .mov
- .wmv, .flv, .webm, .m4v
- .mpg, .mpeg

## System Files

### Main Files
- `/home/pi/video_player.py` - Main Python script
- `/home/pi/.xinitrc` - X11 initialization (auto-starts video player)
- `/home/pi/videos/` - Video folder (add your videos here)

### Service Configuration
- `/etc/systemd/system/video-player-x11.service` - Systemd service file
- `/etc/X11/Xwrapper.config` - X11 configuration (allows service to start X)

## Troubleshooting

### Videos Freezing During Playback

**NEW**: Enhanced logging has been added to help diagnose freezing issues. See `TROUBLESHOOTING_VIDEO_FREEZING.md` for detailed information.

**Quick diagnostic steps:**

1. **Check the detailed logs:**
```bash
# Real-time monitoring
tail -f /tmp/video_player.log

# View recent errors
grep -i "error\|warning" /tmp/video_player.log
```

2. **Analyze your videos:**
```bash
# Run the video analysis script
bash analyze_videos.sh /home/pi/videos

# Check the report
cat /tmp/video_analysis.txt
```

3. **Common causes:**
   - **H.265/HEVC codec**: Limited Pi hardware support
   - **High bitrate**: Videos >10 Mbps may stutter
   - **CPU overload**: Check temperature with `vcgencmd measure_temp`
   - **Thermal throttling**: Ensure adequate cooling

4. **Quick fix - Re-encode problematic videos:**
```bash
ffmpeg -i input.mp4 -c:v libx264 -crf 23 -maxrate 5M -bufsize 10M -c:a aac output.mp4
```

For comprehensive troubleshooting, see **TROUBLESHOOTING_VIDEO_FREEZING.md**

### Service Won't Start

Check the logs:
```bash
sudo journalctl -u video-player-x11.service -n 50
```

### Videos Not Playing

1. Check if service is running:
```bash
sudo systemctl status video-player-x11.service
```

2. Verify videos exist:
```bash
ls -la ~/videos/
```

3. Restart the service:
```bash
sudo systemctl restart video-player-x11.service
```

### Display Issues

If videos don't show on the display, check X server:
```bash
ps aux | grep Xorg
```

The X server should be running on display :0

## Technical Details

- Uses `ffplay` (from ffmpeg package) for video playback
- Requires minimal X11 server (`xserver-xorg` and `xinit`)
- Runs as a systemd service for reliability and auto-start
- Automatically loops through all videos in the folder
