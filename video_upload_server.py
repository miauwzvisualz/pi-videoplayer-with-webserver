#!/usr/bin/env python3
"""
Video Upload Web Server
Simple Flask server for uploading videos via drag-and-drop interface.
"""

from flask import Flask, render_template, request, jsonify, send_from_directory
import os
import subprocess
import json
from pathlib import Path
from werkzeug.utils import secure_filename
import logging

# Configuration
UPLOAD_FOLDER = Path('/home/pi/videos')
ALLOWED_EXTENSIONS = {'.mp4', '.avi', '.mkv', '.mov', '.wmv', '.flv', '.webm', '.m4v', '.mpg', '.mpeg'}
MAX_FILE_SIZE = 5 * 1024 * 1024 * 1024  # 5GB
REQUIRED_WIDTH = 3072
REQUIRED_HEIGHT = 64

app = Flask(__name__)
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
app.config['MAX_CONTENT_LENGTH'] = MAX_FILE_SIZE

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Ensure upload folder exists
UPLOAD_FOLDER.mkdir(exist_ok=True)


def allowed_file(filename):
    """Check if file extension is allowed."""
    return Path(filename).suffix.lower() in ALLOWED_EXTENSIONS


def check_video_resolution(filepath):
    """Check if video has the required resolution using ffprobe."""
    try:
        cmd = [
            'ffprobe',
            '-v', 'error',
            '-select_streams', 'v:0',
            '-show_entries', 'stream=width,height',
            '-of', 'json',
            str(filepath)
        ]
        
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=10)
        
        if result.returncode != 0:
            logger.error(f"ffprobe error: {result.stderr}")
            return False, "Could not read video metadata"
        
        data = json.loads(result.stdout)
        
        if 'streams' not in data or len(data['streams']) == 0:
            return False, "No video stream found"
        
        width = data['streams'][0].get('width')
        height = data['streams'][0].get('height')
        
        if width == REQUIRED_WIDTH and height == REQUIRED_HEIGHT:
            return True, f"{width}x{height}"
        else:
            return False, f"Invalid resolution: {width}x{height}. Required: {REQUIRED_WIDTH}x{REQUIRED_HEIGHT}"
    
    except subprocess.TimeoutExpired:
        return False, "Video analysis timeout"
    except json.JSONDecodeError:
        return False, "Could not parse video metadata"
    except Exception as e:
        logger.error(f"Resolution check error: {e}")
        return False, f"Error checking resolution: {str(e)}"


def restart_video_player():
    """Restart the video player service to reload the playlist."""
    try:
        result = subprocess.run(
            ['sudo', 'systemctl', 'restart', 'video-player-x11.service'],
            capture_output=True,
            text=True,
            timeout=5
        )
        if result.returncode == 0:
            logger.info("Video player service restarted successfully")
            return True
        else:
            logger.error(f"Failed to restart video player: {result.stderr}")
            return False
    except Exception as e:
        logger.error(f"Error restarting video player: {e}")
        return False


def restart_system():
    """Restart the Raspberry Pi."""
    try:
        logger.info("System restart initiated")
        subprocess.Popen(['sudo', 'reboot'])
        return True
    except Exception as e:
        logger.error(f"Error restarting system: {e}")
        return False


def shutdown_system():
    """Shutdown the Raspberry Pi."""
    try:
        logger.info("System shutdown initiated")
        subprocess.Popen(['sudo', 'shutdown', '-h', 'now'])
        return True
    except Exception as e:
        logger.error(f"Error shutting down system: {e}")
        return False


@app.route('/')
def index():
    """Serve the main upload page."""
    return send_from_directory('html', 'index.html')


@app.route('/<path:filename>')
def serve_static(filename):
    """Serve static files (CSS, JS, etc.) from html folder."""
    return send_from_directory('html', filename)


@app.route('/upload', methods=['POST'])
def upload_file():
    """Handle video file upload."""
    try:
        # Check if file is present
        if 'file' not in request.files:
            return jsonify({'success': False, 'error': 'No file provided'}), 400
        
        file = request.files['file']
        
        # Check if filename is empty
        if file.filename == '':
            return jsonify({'success': False, 'error': 'No file selected'}), 400
        
        # Check if file extension is allowed
        if not allowed_file(file.filename):
            return jsonify({
                'success': False,
                'error': f'File type not allowed. Allowed types: {", ".join(ALLOWED_EXTENSIONS)}'
            }), 400
        
        # Secure the filename and save
        filename = secure_filename(file.filename)
        filepath = UPLOAD_FOLDER / filename
        
        # Check if file already exists
        if filepath.exists():
            # Add number suffix to avoid overwriting
            base = filepath.stem
            ext = filepath.suffix
            counter = 1
            while filepath.exists():
                filename = f"{base}_{counter}{ext}"
                filepath = UPLOAD_FOLDER / filename
                counter += 1
        
        file.save(str(filepath))
        
        # Check video resolution
        is_valid, message = check_video_resolution(filepath)
        
        if not is_valid:
            # Delete the file if resolution is invalid
            filepath.unlink()
            logger.warning(f"Rejected upload: {filename} - {message}")
            return jsonify({
                'success': False,
                'error': message
            }), 400
        
        logger.info(f"Uploaded video: {filename} ({filepath.stat().st_size / 1024 / 1024:.2f} MB) - {message}")
        
        # Restart video player to include new video in playlist
        restart_video_player()
        
        return jsonify({
            'success': True,
            'filename': filename,
            'size': filepath.stat().st_size,
            'resolution': message
        })
        
    except Exception as e:
        logger.error(f"Upload error: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/list', methods=['GET'])
def list_videos():
    """List all videos in the upload folder."""
    try:
        videos = []
        for file_path in sorted(UPLOAD_FOLDER.iterdir()):
            if file_path.is_file() and file_path.suffix.lower() in ALLOWED_EXTENSIONS:
                videos.append({
                    'name': file_path.name,
                    'size': file_path.stat().st_size,
                    'modified': file_path.stat().st_mtime
                })
        
        return jsonify({'success': True, 'videos': videos})
        
    except Exception as e:
        logger.error(f"List error: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/delete/<filename>', methods=['DELETE'])
def delete_video(filename):
    """Delete a video file."""
    try:
        filename = secure_filename(filename)
        filepath = UPLOAD_FOLDER / filename
        
        if not filepath.exists():
            return jsonify({'success': False, 'error': 'File not found'}), 404
        
        if not allowed_file(filename):
            return jsonify({'success': False, 'error': 'Invalid file type'}), 400
        
        filepath.unlink()
        logger.info(f"Deleted video: {filename}")
        
        # Restart video player to update playlist
        restart_video_player()
        
        return jsonify({'success': True, 'message': f'Deleted {filename}'})
        
    except Exception as e:
        logger.error(f"Delete error: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/system/restart', methods=['POST'])
def system_restart():
    """Restart the Raspberry Pi."""
    try:
        restart_system()
        return jsonify({'success': True, 'message': 'System restart initiated'})
    except Exception as e:
        logger.error(f"Restart error: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/system/shutdown', methods=['POST'])
def system_shutdown():
    """Shutdown the Raspberry Pi."""
    try:
        shutdown_system()
        return jsonify({'success': True, 'message': 'System shutdown initiated'})
    except Exception as e:
        logger.error(f"Shutdown error: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500


if __name__ == '__main__':
    print("=" * 60)
    print("Video Upload Server")
    print("=" * 60)
    print(f"Upload folder: {UPLOAD_FOLDER}")
    print(f"Allowed formats: {', '.join(sorted(ALLOWED_EXTENSIONS))}")
    print(f"Max file size: {MAX_FILE_SIZE / 1024 / 1024 / 1024:.1f} GB")
    print("-" * 60)
    print("Server starting on http://0.0.0.0:5000")
    print("Access from any device on your network using:")
    print("  http://<raspberry-pi-ip>:5000")
    print("=" * 60)
    
    app.run(host='0.0.0.0', port=5000, debug=False)
