#!/usr/bin/env python3
"""
Audio Player with Loop
Monitors a folder and plays all audio files in a continuous loop.
"""

import os
import sys
import time
import subprocess
import argparse
import logging
from pathlib import Path
from typing import List

# Common audio file extensions
AUDIO_EXTENSIONS = {'.mp3', '.wav', '.flac', '.ogg', '.m4a', '.aac', '.wma', '.opus', '.aiff', '.alac'}

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler('/tmp/audio_player.log')
    ]
)
logger = logging.getLogger(__name__)


class AudioPlayer:
    """Audio player that monitors a folder and plays audio files in a loop."""
    
    def __init__(self, folder_path: str, loop_delay: float = 0, shuffle: bool = False, backend: str = 'auto'):
        """
        Initialize the audio player.
        
        Args:
            folder_path: Path to the folder containing audio files
            loop_delay: Delay in seconds between tracks (default: 0)
            shuffle: Whether to shuffle the playlist (default: False)
            backend: Playback backend ('auto', 'mpv', 'vlc', 'ffplay', 'aplay')
        """
        self.folder_path = Path(folder_path).resolve()
        self.loop_delay = loop_delay
        self.shuffle = shuffle
        self.backend = self._select_backend(backend)
        self.current_process = None
        self._stop_requested = False
        
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
        """Select the best available audio player backend."""
        if backend != 'auto':
            if self._check_command(backend):
                return backend
            else:
                logger.warning(f"{backend} not found, trying auto-detection")
        
        # Priority order for Raspberry Pi and Linux systems
        backends = ['mpv', 'vlc', 'ffplay', 'aplay']
        
        for player in backends:
            if self._check_command(player):
                logger.info(f"Using {player} as audio player backend")
                return player
        
        raise RuntimeError("No suitable audio player found. Please install mpv, vlc, or ffmpeg.")
    
    def get_audio_files(self) -> List[Path]:
        """Get all audio files from the monitored folder."""
        audio_files = []
        
        for file_path in sorted(self.folder_path.iterdir()):
            if file_path.is_file() and file_path.suffix.lower() in AUDIO_EXTENSIONS:
                audio_files.append(file_path)
        
        if self.shuffle:
            import random
            random.shuffle(audio_files)
        
        return audio_files
    
    def play_audio(self, audio_path: Path) -> bool:
        """
        Play a single audio file using the selected backend.
        
        Returns:
            True if audio played successfully, False if interrupted
        """
        logger.info(f"Playing: {audio_path.name}")
        
        try:
            if self.backend == 'mpv':
                cmd = [
                    'mpv',
                    '--no-video',
                    '--really-quiet',
                    str(audio_path)
                ]
            elif self.backend == 'vlc':
                cmd = [
                    'cvlc',
                    '--play-and-exit',
                    '--no-video',
                    '--quiet',
                    str(audio_path)
                ]
            elif self.backend == 'ffplay':
                cmd = [
                    'ffplay',
                    '-nodisp',
                    '-autoexit',
                    '-loglevel', 'error',
                    str(audio_path)
                ]
            elif self.backend == 'aplay':
                # aplay only supports WAV - convert on the fly with ffmpeg if needed
                if audio_path.suffix.lower() == '.wav':
                    cmd = ['aplay', str(audio_path)]
                else:
                    cmd = [
                        'ffplay',
                        '-nodisp',
                        '-autoexit',
                        '-loglevel', 'error',
                        str(audio_path)
                    ]
            else:
                logger.error(f"Unknown backend: {self.backend}")
                return True
            
            self.current_process = subprocess.Popen(
                cmd,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.PIPE,
                text=True
            )
            
            # Wait for playback to finish
            self.current_process.wait()
            
            if self._stop_requested:
                return False
            
            # Log any errors
            stderr = self.current_process.stderr.read()
            if stderr:
                logger.warning(f"Player stderr for {audio_path.name}: {stderr[:500]}")
            
            exit_code = self.current_process.returncode
            self.current_process = None
            
            if exit_code not in [0, 1]:
                logger.error(f"Player exited with code {exit_code} for {audio_path.name}")
            
            return True
            
        except FileNotFoundError:
            logger.error(f"Error: {self.backend} not found.")
            sys.exit(1)
        except KeyboardInterrupt:
            logger.info("\nPlayback interrupted by user.")
            return False
        except Exception as e:
            logger.error(f"Error playing audio {audio_path.name}: {e}", exc_info=True)
            return True  # Continue with next track
    
    def stop(self):
        """Stop the current playback."""
        self._stop_requested = True
        if self.current_process and self.current_process.poll() is None:
            self.current_process.terminate()
            try:
                self.current_process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                self.current_process.kill()
            self.current_process = None
    
    def run(self):
        """Main loop: continuously play audio files from the folder."""
        logger.info("=" * 60)
        logger.info("Audio Player Started")
        logger.info(f"Monitoring folder: {self.folder_path}")
        logger.info(f"Backend: {self.backend}")
        logger.info(f"Log file: /tmp/audio_player.log")
        logger.info("Press Ctrl+C to exit")
        logger.info("=" * 60)
        
        try:
            while not self._stop_requested:
                audio_files = self.get_audio_files()
                
                if not audio_files:
                    logger.warning(f"No audio files found in {self.folder_path}")
                    logger.info("Waiting for audio files... (Ctrl+C to exit)")
                    time.sleep(5)
                    continue
                
                logger.info(f"\nFound {len(audio_files)} audio file(s)")
                logger.info("-" * 60)
                
                for i, audio_file in enumerate(audio_files, 1):
                    if self._stop_requested:
                        break
                    
                    size_mb = audio_file.stat().st_size / (1024 * 1024)
                    logger.info(f"  Track {i}/{len(audio_files)}: {audio_file.name} ({size_mb:.1f} MB)")
                    
                    if not self.play_audio(audio_file):
                        return
                    
                    if self.loop_delay > 0 and not self._stop_requested:
                        logger.info(f"Waiting {self.loop_delay}s before next track...")
                        time.sleep(self.loop_delay)
                
                if not self._stop_requested:
                    logger.info("\n" + "=" * 60)
                    logger.info("End of playlist. Restarting loop...")
                    logger.info("=" * 60 + "\n")
                
        except KeyboardInterrupt:
            logger.info("\n\nAudio player stopped.")
            sys.exit(0)
        except Exception as e:
            logger.error(f"Fatal error in main loop: {e}", exc_info=True)
            sys.exit(1)


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description='Play audio files from a folder in a continuous loop.',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog='''
Examples:
  %(prog)s /path/to/audio
  %(prog)s /path/to/audio --delay 2
  %(prog)s /path/to/audio --shuffle

Supported audio formats:
  .mp3, .wav, .flac, .ogg, .m4a, .aac, .wma, .opus, .aiff, .alac
        '''
    )
    
    parser.add_argument(
        'folder',
        help='Path to folder containing audio files'
    )
    
    parser.add_argument(
        '-d', '--delay',
        type=float,
        default=0,
        help='Delay in seconds between tracks (default: 0)'
    )
    
    parser.add_argument(
        '-s', '--shuffle',
        action='store_true',
        help='Shuffle the playlist order'
    )
    
    parser.add_argument(
        '-b', '--backend',
        choices=['auto', 'mpv', 'vlc', 'ffplay', 'aplay'],
        default='auto',
        help='Audio player backend to use (default: auto)'
    )
    
    args = parser.parse_args()
    
    try:
        player = AudioPlayer(args.folder, args.delay, args.shuffle, args.backend)
        player.run()
    except ValueError as e:
        print(f"Error: {e}")
        sys.exit(1)
    except Exception as e:
        print(f"Unexpected error: {e}")
        sys.exit(1)


if __name__ == '__main__':
    main()
