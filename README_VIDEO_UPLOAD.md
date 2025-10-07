# Video Upload Web Server

A simple web interface for uploading videos to your Raspberry Pi via drag-and-drop.

## Features

- 🎬 **Drag & Drop Interface** - Simply drag videos from your computer
- 📤 **Multi-file Upload** - Upload multiple videos at once
- 📊 **Progress Tracking** - Real-time upload progress
- 📂 **File Management** - View and delete uploaded videos
- 🎨 **Modern UI** - Beautiful, responsive interface
- 🔒 **Secure** - File validation and sanitization

## Installation

1. Install Python dependencies:
```bash
pip3 install -r requirements.txt
```

## Usage

### Start the Web Server

```bash
python3 video_upload_server.py
```

The server will start on port 5000 and be accessible from any device on your network.

### Access the Upload Interface

Open a web browser and navigate to:
- **From Raspberry Pi:** http://localhost:5000
- **From other devices:** http://\<raspberry-pi-ip\>:5000

Replace `<raspberry-pi-ip>` with your Raspberry Pi's IP address (find it with `hostname -I`).

### Upload Videos

1. **Drag and Drop:** Simply drag video files into the drop zone
2. **Browse:** Click "Browse Files" to select videos from your device
3. **Monitor:** Watch the upload progress in real-time
4. **Manage:** View uploaded videos and delete them if needed

## Supported Video Formats

- MP4 (.mp4)
- AVI (.avi)
- MKV (.mkv)
- MOV (.mov)
- WMV (.wmv)
- FLV (.flv)
- WebM (.webm)
- M4V (.m4v)
- MPEG (.mpg, .mpeg)

## Configuration

Edit `video_upload_server.py` to customize:

- **Upload folder:** Change `UPLOAD_FOLDER` (default: `/home/pi/videos`)
- **Port:** Change port in `app.run()` (default: 5000)
- **Max file size:** Change `MAX_FILE_SIZE` (default: 5GB)

## Running as a Service (Optional)

To automatically start the server on boot, create a systemd service:

```bash
sudo nano /etc/systemd/system/video-upload.service
```

Add:
```ini
[Unit]
Description=Video Upload Web Server
After=network.target

[Service]
Type=simple
User=pi
WorkingDirectory=/home/pi
ExecStart=/usr/bin/python3 /home/pi/video_upload_server.py
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
```

Enable and start:
```bash
sudo systemctl enable video-upload.service
sudo systemctl start video-upload.service
```

## Integration with Video Player

The uploaded videos are automatically saved to the `/home/pi/videos` folder, which is monitored by the video player (`video_player.py`). Start both services for a complete solution:

1. **Terminal 1:** Start video player
   ```bash
   python3 video_player.py videos
   ```

2. **Terminal 2:** Start upload server
   ```bash
   python3 video_upload_server.py
   ```

## Security Notes

- The server is accessible from any device on your network
- Consider adding authentication for production use
- Firewall configuration may be needed to allow port 5000
- Files are validated for proper video extensions

## Troubleshooting

### Cannot access from other devices
- Check firewall: `sudo ufw allow 5000`
- Verify IP address: `hostname -I`
- Ensure devices are on same network

### Upload fails
- Check disk space: `df -h`
- Verify folder permissions: `ls -la /home/pi/videos`
- Check file size limit (default 5GB)

### Port already in use
- Change port in `video_upload_server.py`
- Or stop conflicting service: `sudo lsof -i :5000`
