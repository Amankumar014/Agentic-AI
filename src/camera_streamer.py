"""
Thread-safe camera streamer for MJPEG video streaming.
Manages a shared camera instance and provides frames for multiple concurrent viewers.
"""
import cv2
import threading
import time
from typing import Optional
import logging

from src.config import get_settings

logger = logging.getLogger(__name__)


class CameraStreamer:
    """
    Thread-safe camera streamer that manages a shared camera instance.
    Allows multiple concurrent viewers to access the same camera feed.
    """
    
    def __init__(self, camera_index: int = 0, fps: int = 15, 
                 max_width: int = 1280, max_height: int = 720,
                 jpeg_quality: int = 85):
        """
        Initialize the camera streamer.
        
        Args:
            camera_index: Camera device index (default: 0)
            fps: Target frames per second for streaming
            max_width: Maximum frame width (0 = no limit)
            max_height: Maximum frame height (0 = no limit)
            jpeg_quality: JPEG encoding quality (1-100)
        """
        self.camera_index = camera_index
        self.fps = fps
        self.max_width = max_width
        self.max_height = max_height
        self.jpeg_quality = jpeg_quality
        self.frame_delay = 1.0 / fps if fps > 0 else 0.1
        
        # Thread synchronization
        self._lock = threading.Lock()
        self._camera: Optional[cv2.VideoCapture] = None
        self._running = False
        self._frame_thread: Optional[threading.Thread] = None
        
        # Latest frame cache (thread-safe queue)
        self._latest_frame: Optional[bytes] = None
        self._frame_timestamp = 0.0
        
        # Viewer tracking
        self._viewer_count = 0
        self._viewer_lock = threading.Lock()
        
        logger.info(f"CameraStreamer initialized: index={camera_index}, fps={fps}")
    
    def _open_camera(self) -> bool:
        """Open the camera if not already open."""
        with self._lock:
            if self._camera is not None and self._camera.isOpened():
                return True
            
            try:
                self._camera = cv2.VideoCapture(self.camera_index)
                if not self._camera.isOpened():
                    logger.error(f"Failed to open camera {self.camera_index}")
                    return False
                
                # Set camera properties for better performance
                self._camera.set(cv2.CAP_PROP_BUFFERSIZE, 1)  # Reduce latency
                
                # Get actual camera properties
                width = int(self._camera.get(cv2.CAP_PROP_FRAME_WIDTH))
                height = int(self._camera.get(cv2.CAP_PROP_FRAME_HEIGHT))
                logger.info(f"Camera opened: {width}x{height}")
                return True
            
            except Exception as e:
                logger.error(f"Error opening camera: {e}")
                return False
    
    def _close_camera(self):
        """Close the camera."""
        with self._lock:
            if self._camera is not None:
                self._camera.release()
                self._camera = None
                logger.info("Camera closed")
    
    def _capture_frame(self) -> Optional[bytes]:
        """Capture and encode a single frame."""
        try:
            with self._lock:
                if self._camera is None or not self._camera.isOpened():
                    return None
                
                ret, frame = self._camera.read()
                if not ret or frame is None:
                    return None
            
            # Resize if needed
            if self.max_width > 0 or self.max_height > 0:
                height, width = frame.shape[:2]
                
                if self.max_width > 0 and width > self.max_width:
                    scale = self.max_width / width
                    new_width = self.max_width
                    new_height = int(height * scale)
                    frame = cv2.resize(frame, (new_width, new_height))
                
                if self.max_height > 0:
                    height, width = frame.shape[:2]
                    if height > self.max_height:
                        scale = self.max_height / height
                        new_width = int(width * scale)
                        new_height = self.max_height
                        frame = cv2.resize(frame, (new_width, new_height))
            
            # Encode as JPEG
            encode_params = [cv2.IMWRITE_JPEG_QUALITY, self.jpeg_quality]
            success, buffer = cv2.imencode('.jpg', frame, encode_params)
            
            if not success:
                return None
            
            return buffer.tobytes()
        
        except Exception as e:
            logger.error(f"Error capturing frame: {e}")
            return None
    
    def _frame_loop(self):
        """Main loop for capturing frames continuously."""
        logger.info("Frame capture loop started")
        
        while self._running:
            try:
                # Open camera if needed
                if not self._open_camera():
                    logger.warning("Camera not available, retrying in 1 second...")
                    time.sleep(1.0)
                    continue
                
                # Capture frame
                frame_bytes = self._capture_frame()
                
                if frame_bytes is not None:
                    with self._lock:
                        self._latest_frame = frame_bytes
                        self._frame_timestamp = time.time()
                
                # Control frame rate
                time.sleep(self.frame_delay)
            
            except Exception as e:
                logger.error(f"Error in frame loop: {e}")
                time.sleep(0.5)
        
        # Cleanup
        self._close_camera()
        logger.info("Frame capture loop stopped")
    
    def start(self):
        """Start the camera streamer."""
        with self._lock:
            if self._running:
                logger.warning("Camera streamer already running")
                return
            
            self._running = True
            self._frame_thread = threading.Thread(target=self._frame_loop, daemon=True)
            self._frame_thread.start()
            logger.info("Camera streamer started")
    
    def stop(self):
        """Stop the camera streamer."""
        with self._lock:
            if not self._running:
                return
            
            self._running = False
        
        if self._frame_thread is not None:
            self._frame_thread.join(timeout=5.0)
        
        self._close_camera()
        logger.info("Camera streamer stopped")
    
    def add_viewer(self):
        """Register a new viewer."""
        with self._viewer_lock:
            self._viewer_count += 1
            if self._viewer_count == 1:
                # First viewer - start the streamer
                self.start()
            logger.info(f"Viewer added (total: {self._viewer_count})")
    
    def remove_viewer(self):
        """Unregister a viewer."""
        with self._viewer_lock:
            if self._viewer_count > 0:
                self._viewer_count -= 1
                logger.info(f"Viewer removed (total: {self._viewer_count})")
                
                if self._viewer_count == 0:
                    # Last viewer - stop the streamer
                    self.stop()
    
    def get_frame(self) -> Optional[bytes]:
        """
        Get the latest frame.
        
        Returns:
            JPEG-encoded frame bytes, or None if no frame available
        """
        with self._lock:
            return self._latest_frame
    
    def is_available(self) -> bool:
        """Check if camera is available and streaming."""
        with self._lock:
            return self._running and self._latest_frame is not None


# Global camera streamer instance
_streamer: Optional[CameraStreamer] = None
_streamer_lock = threading.Lock()


def get_camera_streamer() -> CameraStreamer:
    """
    Get or create the global camera streamer instance.
    
    Returns:
        CameraStreamer: The global camera streamer instance
    """
    global _streamer
    
    with _streamer_lock:
        if _streamer is None:
            settings = get_settings()
            _streamer = CameraStreamer(
                camera_index=settings.CAMERA_INDEX,
                fps=settings.STREAM_FPS,
                max_width=settings.STREAM_MAX_WIDTH,
                max_height=settings.STREAM_MAX_HEIGHT,
                jpeg_quality=settings.STREAM_JPEG_QUALITY
            )
        
        return _streamer


def cleanup_camera_streamer():
    """Cleanup the global camera streamer."""
    global _streamer
    
    with _streamer_lock:
        if _streamer is not None:
            _streamer.stop()
            _streamer = None
