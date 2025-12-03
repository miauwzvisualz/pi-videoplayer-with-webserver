#!/usr/bin/env python3
"""
Video Player with FFmpeg Loop
Monitors a folder and plays all videos in a continuous loop using ffmpeg.
"""

import os
import sys
import time
import subprocess
import argparse
import tempfile
import logging
import threading
from pathlib import Path
from typing import List

# Common video file extensions
VIDEO_EXTENSIONS = {'.mp4', '.avi', '.mkv', '.mov', '.wmv', '.flv', '.webm', '.m4v', '.mpg', '.mpeg'}

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler('/tmp/video_player.log')
    ]
)
logger = logging.getLogger(__name__)


class VideoPlayer:
    """Video player that monitors a folder and plays videos in a loop."""
    
    def __init__(self, folder_path: str, loop_delay: float = 0, shuffle: bool = False, backend: str = 'auto', crop_filter: str = None):
        """
        Initialize the video player.
        
        Args:
            folder_path: Path to the folder containing videos
            loop_delay: Delay in seconds between videos (default: 0)
            shuffle: Whether to shuffle the playlist (default: False)
            backend: Playback backend ('auto', 'vlc', 'omxplayer', 'ffplay', 'mpv')
            crop_filter: FFmpeg crop/filter_complex string (default: None)
        """
        self.folder_path = Path(folder_path).resolve()
        self.loop_delay = loop_delay
        self.shuffle = shuffle
        self.backend = self._select_backend(backend)
        self.crop_filter = crop_filter
        self.playback_timeout = 300  # 5 minutes timeout for detecting frozen playback
        
        if not self.folder_path.exists():
            raise ValueError(f"Folder does not exist: {self.folder_path}")
        
        if not self.folder_path.is_dir():
            raise ValueError(f"Path is not a directory: {self.folder_path}")
    
    def _check_command(self, cmd: str) -> bool:
        """Check if a command exists in PATH."""
        try:
            subprocess.run(['which', cmd], check=True, capture_output=True)
            return True
        except subprocess.CalledProcessError:
            return False
    
    def _select_backend(self, backend: str) -> str:
        """Select the best available video player backend."""
        if backend != 'auto':
            if self._check_command(backend):
                return backend
            else:
                print(f"Warning: {backend} not found, trying auto-detection")
        
        # Priority order for Raspberry Pi and Linux systems
        backends = ['vlc', 'omxplayer', 'mpv', 'ffplay']
        
        for player in backends:
            if self._check_command(player):
                logger.info(f"Using {player} as video player backend")
                return player
        
        raise RuntimeError("No suitable video player found. Please install vlc, mpv, omxplayer, or ffmpeg.")
    
    def get_video_files(self) -> List[Path]:
        """Get all video files from the monitored folder."""
        video_files = []
        
        for file_path in sorted(self.folder_path.iterdir()):
            if file_path.is_file() and file_path.suffix.lower() in VIDEO_EXTENSIONS:
                video_files.append(file_path)
        
        if self.shuffle:
            import random
            random.shuffle(video_files)
        
        return video_files
    
    def create_concat_file(self, video_files: List[Path], repeat: int = 1000) -> str:
        """Create a temporary concat file for gapless playback."""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False) as f:
            # Repeat the playlist many times to avoid restarts
            for _ in range(repeat):
                for video in video_files:
                    # Escape single quotes in filenames
                    safe_path = str(video).replace("'", "'\\''")
                    f.write(f"file '{safe_path}'\n")
            return f.name
    
    def play_video(self, video_path: Path) -> bool:
        """
        Play a single video using the selected backend.
        
        Args:
            video_path: Path to the video file
            
        Returns:
            True if video played successfully, False otherwise
        """
        logger.info(f"Playing: {video_path.name}")
        
        try:
            if self.backend == 'vlc':
                # VLC with console interface (works without X11)
                cmd = [
                    'vlc',
                    '--play-and-exit',
                    '--no-video-title-show',
                    '--quiet',
                    '--fullscreen',
                    str(video_path)
                ]
            elif self.backend == 'omxplayer':
                # omxplayer (optimized for Raspberry Pi)
                cmd = [
                    'omxplayer',
                    '--no-osd',
                    str(video_path)
                ]
            elif self.backend == 'mpv':
                # mpv (works well on various systems)
                cmd = [
                    'mpv',
                    '--fs',
                    '--no-terminal',
                    '--really-quiet',
                    str(video_path)
                ]
            elif self.backend == 'ffplay':
                # ffplay with environment tweaks for software rendering
                cmd = [
                    'ffplay',
                    '-autoexit',
                    '-fs',
                    '-noborder',
                    '-left', '0',
                    '-top', '0',
                    '-loglevel', 'error',
                    str(video_path)
                ]
            else:
                print(f"Unknown backend: {self.backend}")
                return True
            
            # Set environment for better compatibility
            env = os.environ.copy()
            
            # If no DISPLAY is set, try to use the default display
            if 'DISPLAY' not in env or not env['DISPLAY']:
                env['DISPLAY'] = ':0'
            
            if self.backend == 'ffplay':
                # Try software rendering for ffplay if display connection fails
                env['SDL_VIDEODRIVER'] = 'x11'  # Try X11 first
                env['SDL_VIDEO_WINDOW_POS'] = '0,0'  # Position at top-left
                env['SDL_NOMOUSE'] = '1'  # Hide mouse cursor
            
            result = subprocess.run(cmd, env=env, check=False, capture_output=True, text=True)
            
            # Log any errors from stderr
            if result.stderr:
                logger.warning(f"Player stderr for {video_path.name}: {result.stderr[:500]}")
            
            # Return True if player exited normally
            if result.returncode not in [0, 1]:
                logger.error(f"Player exited with code {result.returncode} for {video_path.name}")
            return result.returncode in [0, 1]
            
        except FileNotFoundError:
            logger.error(f"Error: {self.backend} not found.")
            sys.exit(1)
        except KeyboardInterrupt:
            logger.info("\nPlayback interrupted by user.")
            return False
        except Exception as e:
            logger.error(f"Error playing video {video_path.name}: {e}", exc_info=True)
            return True  # Continue with next video
    
    def _log_stderr(self, proc, name: str):
        """Thread function to log stderr output from a process."""
        try:
            for line in proc.stderr:
                line = line.strip()
                if line:
                    logger.warning(f"{name}: {line}")
        except Exception as e:
            logger.error(f"Error reading {name} stderr: {e}")
    
    def play_playlist_gapless(self, video_files: List[Path]) -> bool:
        """Play all videos in a gapless loop using ffmpeg pipe to ffplay."""
        logger.info(f"Playing {len(video_files)} video(s) in gapless mode")
        
        # Log video file details
        for i, video in enumerate(video_files, 1):
            size_mb = video.stat().st_size / (1024 * 1024)
            logger.info(f"  {i}. {video.name} ({size_mb:.1f} MB)")
        
        # Create concat file
        concat_file = self.create_concat_file(video_files)
        
        try:
            # Set environment
            env = os.environ.copy()
            if 'DISPLAY' not in env or not env['DISPLAY']:
                env['DISPLAY'] = ':0'
            
            if self.backend == 'ffplay':
                env['SDL_VIDEODRIVER'] = 'x11'
                env['SDL_VIDEO_WINDOW_POS'] = '0,0'
                env['SDL_NOMOUSE'] = '1'
            
            # Use ffmpeg to process and pipe to ffplay for gapless playback
            ffmpeg_cmd = [
                'ffmpeg',
                '-f', 'concat',
                '-safe', '0',
                '-i', concat_file
            ]
            
            # Add crop/scale filters if specified
            if self.crop_filter:
                logger.info(f"Applying video filter: {self.crop_filter}")
                # Use filter_complex if the filter contains multiple operations
                if '[' in self.crop_filter or 'stack' in self.crop_filter or ';' in self.crop_filter:
                    ffmpeg_cmd.extend(['-filter_complex', self.crop_filter])
                else:
                    ffmpeg_cmd.extend(['-vf', self.crop_filter])
                # Use hardware acceleration if available on Raspberry Pi
                ffmpeg_cmd.extend(['-c:v', 'libx264', '-preset', 'ultrafast', '-tune', 'zerolatency', '-crf', '23'])
                logger.warning("Using software encoding - this may cause performance issues on Raspberry Pi")
            else:
                # No filtering, just copy
                ffmpeg_cmd.extend(['-c', 'copy'])
                logger.info("Using stream copy (no re-encoding)")
            
            ffmpeg_cmd.extend(['-f', 'matroska', '-'])
            
            ffplay_cmd = [
                'ffplay',
                '-fs',
                '-noborder',
                '-left', '0',
                '-top', '0',
                '-autoexit',
                '-loglevel', 'error',
                '-'
            ]
            
            logger.info(f"Starting ffmpeg: {' '.join(ffmpeg_cmd[:10])}...")
            logger.info(f"Starting ffplay: {' '.join(ffplay_cmd)}")
            
            ffmpeg_proc = subprocess.Popen(
                ffmpeg_cmd, 
                stdout=subprocess.PIPE, 
                stderr=subprocess.PIPE,
                text=True,
                bufsize=1
            )
            ffplay_proc = subprocess.Popen(
                ffplay_cmd, 
                stdin=ffmpeg_proc.stdout, 
                env=env, 
                stderr=subprocess.PIPE,
                text=True,
                bufsize=1
            )
            
            # Start threads to log stderr from both processes
            ffmpeg_thread = threading.Thread(target=self._log_stderr, args=(ffmpeg_proc, "ffmpeg"), daemon=True)
            ffplay_thread = threading.Thread(target=self._log_stderr, args=(ffplay_proc, "ffplay"), daemon=True)
            ffmpeg_thread.start()
            ffplay_thread.start()
            
            # Allow ffmpeg to receive SIGPIPE if ffplay exits
            ffmpeg_proc.stdout.close()
            
            # Wait for ffplay to finish with periodic status checks
            logger.info("Playback started, monitoring processes...")
            last_check = time.time()
            
            while ffplay_proc.poll() is None:
                time.sleep(5)
                elapsed = time.time() - last_check
                
                # Check if ffmpeg died unexpectedly
                if ffmpeg_proc.poll() is not None and ffplay_proc.poll() is None:
                    logger.error("ffmpeg process died unexpectedly")
                    ffplay_proc.terminate()
                    break
                
                # Log status every 30 seconds
                if elapsed >= 30:
                    logger.info(f"Playback running... (ffmpeg: {ffmpeg_proc.poll()}, ffplay: {ffplay_proc.poll()})")
                    last_check = time.time()
            
            # Get exit codes
            ffplay_code = ffplay_proc.wait()
            ffmpeg_code = ffmpeg_proc.wait()
            
            logger.info(f"Playback ended - ffmpeg exit code: {ffmpeg_code}, ffplay exit code: {ffplay_code}")
            
            return True
            
        except KeyboardInterrupt:
            logger.info("\nPlayback interrupted by user.")
            return False
        except Exception as e:
            logger.error(f"Error playing playlist: {e}", exc_info=True)
            return True
        finally:
            # Clean up concat file
            try:
                os.unlink(concat_file)
            except:
                pass
    
    def run(self):
        """Main loop: continuously play videos from the folder."""
        logger.info("=" * 60)
        logger.info("Video Player Started (Gapless Mode)")
        logger.info(f"Monitoring folder: {self.folder_path}")
        logger.info(f"Backend: {self.backend}")
        logger.info(f"Log file: /tmp/video_player.log")
        logger.info("Press Ctrl+C to exit")
        logger.info("=" * 60)
        
        try:
            while True:
                video_files = self.get_video_files()
                
                if not video_files:
                    logger.warning(f"No video files found in {self.folder_path}")
                    logger.info("Waiting for videos... (Ctrl+C to exit)")
                    time.sleep(5)
                    continue
                
                logger.info(f"\nFound {len(video_files)} video(s)")
                logger.info("-" * 60)
                
                # Play all videos in gapless mode
                if not self.play_playlist_gapless(video_files):
                    return
                
                if self.loop_delay > 0:
                    logger.info(f"Waiting {self.loop_delay}s before next loop...")
                    time.sleep(self.loop_delay)
                
                logger.info("\n" + "=" * 60)
                logger.info("End of playlist. Restarting loop...")
                logger.info("=" * 60 + "\n")
                
        except KeyboardInterrupt:
            logger.info("\n\nVideo player stopped.")
            sys.exit(0)
        except Exception as e:
            logger.error(f"Fatal error in main loop: {e}", exc_info=True)
            sys.exit(1)


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description='Play videos from a folder in a continuous loop using ffmpeg.',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog='''
Examples:
  %(prog)s /path/to/videos
  %(prog)s /path/to/videos --delay 2
  %(prog)s /path/to/videos --shuffle

Supported video formats:
  .mp4, .avi, .mkv, .mov, .wmv, .flv, .webm, .m4v, .mpg, .mpeg
        '''
    )
    
    parser.add_argument(
        'folder',
        help='Path to folder containing video files'
    )
    
    parser.add_argument(
        '-d', '--delay',
        type=float,
        default=0,
        help='Delay in seconds between videos (default: 0)'
    )
    
    parser.add_argument(
        '-s', '--shuffle',
        action='store_true',
        help='Shuffle the playlist order'
    )
    
    parser.add_argument(
        '-b', '--backend',
        choices=['auto', 'vlc', 'omxplayer', 'mpv', 'ffplay'],
        default='auto',
        help='Video player backend to use (default: auto)'
    )
    
    parser.add_argument(
        '-c', '--crop',
        type=str,
        default=None,
        help='FFmpeg crop/filter_complex (e.g., "[0:v]crop=1920:64:0:0[top];[0:v]crop=1152:64:1920:0[bottom];[top][bottom]vstack")'
    )
    
    args = parser.parse_args()
    
    try:
        player = VideoPlayer(args.folder, args.delay, args.shuffle, args.backend, args.crop)
        player.run()
    except ValueError as e:
        print(f"Error: {e}")
        sys.exit(1)
    except Exception as e:
        print(f"Unexpected error: {e}")
        sys.exit(1)


if __name__ == '__main__':
    main()
