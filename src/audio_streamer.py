"""
Audio streamer for continuous microphone capture.

Provides thread-safe audio streaming with rolling buffer similar to camera_streamer.py.
Captures audio continuously and provides access to latest audio chunks for analysis.
"""
import logging
import threading
import time
from typing import Optional
import numpy as np

from src.config import get_settings

logger = logging.getLogger(__name__)


class AudioStreamer:
    """
    Thread-safe audio streamer with continuous capture and rolling buffer.
    
    Similar to CameraStreamer, manages audio device lifecycle based on viewer count.
    Provides latest audio chunks for analysis and streaming.
    """
    
    def __init__(self, buffer_duration: int = 5):
        """
        Initialize audio streamer.
        
        Args:
            buffer_duration: Seconds of audio to keep in rolling buffer (default: 5)
        """
        self.settings = get_settings()
        self.buffer_duration = buffer_duration
        
        # Audio capture settings
        self.sample_rate = self.settings.AUDIO_SAMPLE_RATE
        self.channels = 1  # Mono
        
        # Rolling buffer (circular buffer for recent audio)
        buffer_samples = self.sample_rate * self.buffer_duration
        self._audio_buffer = np.zeros(buffer_samples, dtype=np.float32)
        self._buffer_position = 0
        self._buffer_lock = threading.Lock()
        
        # Latest chunk for analysis (last N seconds)
        self._latest_chunk: Optional[np.ndarray] = None
        self._chunk_lock = threading.Lock()
        
        # Viewer management (start/stop based on demand)
        self._viewers = 0
        self._viewers_lock = threading.Lock()
        
        # Capture thread
        self._capture_thread: Optional[threading.Thread] = None
        self._running = False
        self._thread_lock = threading.Lock()
        
        # Audio device
        self._stream = None
        self._audio_available = False
        
        logger.info(f"AudioStreamer initialized (sample_rate={self.sample_rate}Hz, buffer={buffer_duration}s)")
    
    def add_viewer(self):
        """
        Add a viewer/listener.
        Starts audio capture if this is the first viewer.
        """
        with self._viewers_lock:
            self._viewers += 1
            logger.info(f"Audio viewer added (total: {self._viewers})")
            
            # Start capture thread if first viewer
            if self._viewers == 1:
                self._start_capture()
    
    def remove_viewer(self):
        """
        Remove a viewer/listener.
        Stops audio capture if no viewers remain.
        """
        with self._viewers_lock:
            self._viewers = max(0, self._viewers - 1)
            logger.info(f"Audio viewer removed (total: {self._viewers})")
            
            # Stop capture thread if no viewers
            if self._viewers == 0:
                self._stop_capture()
    
    def _start_capture(self):
        """Start audio capture thread."""
        with self._thread_lock:
            if self._running:
                return
            
            self._running = True
            self._capture_thread = threading.Thread(
                target=self._capture_loop,
                daemon=True,
                name="AudioStreamer"
            )
            self._capture_thread.start()
            logger.info("Audio capture started")
    
    def _stop_capture(self):
        """Stop audio capture thread."""
        with self._thread_lock:
            if not self._running:
                return
            
            self._running = False
            
            # Close audio stream
            if self._stream is not None:
                try:
                    self._stream.stop()
                    self._stream.close()
                except Exception as e:
                    logger.error(f"Error closing audio stream: {e}")
                finally:
                    self._stream = None
            
            # Wait for thread to finish
            if self._capture_thread:
                self._capture_thread.join(timeout=2.0)
            
            logger.info("Audio capture stopped")
    
    def _capture_loop(self):
        """
        Main audio capture loop.
        Continuously captures audio from microphone.
        """
        try:
            import sounddevice as sd
            self._audio_available = True
        except ImportError:
            logger.error("sounddevice not installed - audio capture unavailable")
            self._audio_available = False
            return
        
        logger.info("Starting audio capture loop...")
        
        # Chunk size for capture (e.g., 0.5 seconds per read)
        chunk_duration = 0.5  # seconds
        chunk_size = int(self.sample_rate * chunk_duration)
        
        try:
            # Open audio input stream
            self._stream = sd.InputStream(
                samplerate=self.sample_rate,
                channels=self.channels,
                dtype='float32',
                blocksize=chunk_size,
                device=None  # Use default device
            )
            self._stream.start()
            logger.info(f"Audio stream opened (device: default, sample_rate={self.sample_rate}Hz)")
            
            while self._running:
                try:
                    # Read audio chunk
                    audio_chunk, overflowed = self._stream.read(chunk_size)
                    
                    if overflowed:
                        logger.warning("Audio buffer overflow - some samples lost")
                    
                    # Convert to 1D array if needed
                    if audio_chunk.ndim > 1:
                        audio_chunk = audio_chunk.flatten()
                    
                    # Update rolling buffer
                    self._update_buffer(audio_chunk)
                    
                    # Update latest chunk for analysis
                    with self._chunk_lock:
                        self._latest_chunk = audio_chunk.copy()
                
                except Exception as e:
                    if self._running:
                        logger.error(f"Error reading audio: {e}")
                        time.sleep(0.1)
        
        except Exception as e:
            logger.error(f"Error in audio capture loop: {e}", exc_info=True)
        
        finally:
            # Cleanup
            if self._stream is not None:
                try:
                    self._stream.stop()
                    self._stream.close()
                except Exception:
                    pass
            logger.info("Audio capture loop stopped")
    
    def _update_buffer(self, audio_chunk: np.ndarray):
        """
        Update rolling buffer with new audio chunk.
        
        Args:
            audio_chunk: New audio samples to add
        """
        with self._buffer_lock:
            chunk_len = len(audio_chunk)
            buffer_len = len(self._audio_buffer)
            
            # Calculate write positions
            start_pos = self._buffer_position
            end_pos = start_pos + chunk_len
            
            if end_pos <= buffer_len:
                # Fits in buffer without wrapping
                self._audio_buffer[start_pos:end_pos] = audio_chunk
            else:
                # Wrap around to beginning
                first_part = buffer_len - start_pos
                self._audio_buffer[start_pos:] = audio_chunk[:first_part]
                self._audio_buffer[:chunk_len - first_part] = audio_chunk[first_part:]
            
            # Update position (circular)
            self._buffer_position = end_pos % buffer_len
    
    def get_latest_chunk(self) -> Optional[np.ndarray]:
        """
        Get the latest audio chunk for analysis.
        
        Returns:
            numpy array of audio samples (float32, mono) or None if no audio available
        """
        with self._chunk_lock:
            if self._latest_chunk is None:
                return None
            return self._latest_chunk.copy()
    
    def get_buffer(self, duration: Optional[float] = None) -> Optional[np.ndarray]:
        """
        Get recent audio from rolling buffer.
        
        Args:
            duration: Seconds of audio to retrieve (default: full buffer)
        
        Returns:
            numpy array of audio samples or None if no audio available
        """
        with self._buffer_lock:
            if duration is None:
                # Return full buffer
                return self._audio_buffer.copy()
            
            # Return last N seconds
            samples = int(duration * self.sample_rate)
            samples = min(samples, len(self._audio_buffer))
            
            # Extract from circular buffer
            end_pos = self._buffer_position
            start_pos = (end_pos - samples) % len(self._audio_buffer)
            
            if start_pos < end_pos:
                # No wrap
                return self._audio_buffer[start_pos:end_pos].copy()
            else:
                # Wrap around
                return np.concatenate([
                    self._audio_buffer[start_pos:],
                    self._audio_buffer[:end_pos]
                ])
    
    def is_available(self) -> bool:
        """Check if audio capture is available."""
        return self._audio_available
    
    def is_running(self) -> bool:
        """Check if audio capture is currently running."""
        return self._running
    
    def get_sample_rate(self) -> int:
        """Get audio sample rate."""
        return self.sample_rate


# Global audio streamer instance
_audio_streamer: Optional[AudioStreamer] = None
_streamer_lock = threading.Lock()


def get_audio_streamer() -> AudioStreamer:
    """
    Get or create the global audio streamer instance.
    
    Returns:
        AudioStreamer: The global audio streamer
    """
    global _audio_streamer
    
    with _streamer_lock:
        if _audio_streamer is None:
            _audio_streamer = AudioStreamer()
        
        return _audio_streamer


def cleanup_audio_streamer():
    """
    Cleanup the global audio streamer.
    Should be called on application shutdown.
    """
    global _audio_streamer
    
    with _streamer_lock:
        if _audio_streamer is not None:
            _audio_streamer._stop_capture()
            _audio_streamer = None
            logger.info("Audio streamer cleaned up")
