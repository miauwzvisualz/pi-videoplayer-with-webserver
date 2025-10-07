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
from pathlib import Path
from typing import List

# Common video file extensions
VIDEO_EXTENSIONS = {'.mp4', '.avi', '.mkv', '.mov', '.wmv', '.flv', '.webm', '.m4v', '.mpg', '.mpeg'}


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
                print(f"Using {player} as video player backend")
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
        print(f"Playing: {video_path.name}")
        
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
            
            result = subprocess.run(cmd, env=env, check=False, stderr=subprocess.PIPE)
            
            # Return True if player exited normally
            return result.returncode in [0, 1]
            
        except FileNotFoundError:
            print(f"Error: {self.backend} not found.")
            sys.exit(1)
        except KeyboardInterrupt:
            print("\nPlayback interrupted by user.")
            return False
        except Exception as e:
            print(f"Error playing video: {e}")
            return True  # Continue with next video
    
    def play_playlist_gapless(self, video_files: List[Path]) -> bool:
        """Play all videos in a gapless loop using ffmpeg pipe to ffplay."""
        print(f"Playing {len(video_files)} video(s) in gapless mode")
        
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
                # Use filter_complex if the filter contains multiple operations
                if '[' in self.crop_filter or 'stack' in self.crop_filter or ';' in self.crop_filter:
                    ffmpeg_cmd.extend(['-filter_complex', self.crop_filter])
                else:
                    ffmpeg_cmd.extend(['-vf', self.crop_filter])
                ffmpeg_cmd.extend(['-c:v', 'libx264', '-preset', 'ultrafast', '-tune', 'zerolatency'])
            else:
                # No filtering, just copy
                ffmpeg_cmd.extend(['-c', 'copy'])
            
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
            
            ffmpeg_proc = subprocess.Popen(ffmpeg_cmd, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL)
            ffplay_proc = subprocess.Popen(ffplay_cmd, stdin=ffmpeg_proc.stdout, env=env, stderr=subprocess.DEVNULL)
            
            # Allow ffmpeg to receive SIGPIPE if ffplay exits
            ffmpeg_proc.stdout.close()
            
            # Wait for ffplay to finish
            ffplay_proc.wait()
            ffmpeg_proc.wait()
            
            return True
            
        except KeyboardInterrupt:
            print("\nPlayback interrupted by user.")
            return False
        except Exception as e:
            print(f"Error playing playlist: {e}")
            return True
        finally:
            # Clean up concat file
            try:
                os.unlink(concat_file)
            except:
                pass
    
    def run(self):
        """Main loop: continuously play videos from the folder."""
        print(f"Video Player Started (Gapless Mode)")
        print(f"Monitoring folder: {self.folder_path}")
        print(f"Press Ctrl+C to exit")
        print("-" * 60)
        
        try:
            while True:
                video_files = self.get_video_files()
                
                if not video_files:
                    print(f"No video files found in {self.folder_path}")
                    print("Waiting for videos... (Ctrl+C to exit)")
                    time.sleep(5)
                    continue
                
                print(f"\nFound {len(video_files)} video(s)")
                print("-" * 60)
                
                # Play all videos in gapless mode
                if not self.play_playlist_gapless(video_files):
                    return
                
                if self.loop_delay > 0:
                    time.sleep(self.loop_delay)
                
                print("\n" + "=" * 60)
                print("End of playlist. Restarting loop...")
                print("=" * 60 + "\n")
                
        except KeyboardInterrupt:
            print("\n\nVideo player stopped.")
            sys.exit(0)


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
