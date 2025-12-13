"""
Real-time detection broadcaster for Live Dashboard.

Continuously runs detections on camera frames and broadcasts results
to connected WebSocket clients.
"""
import asyncio
import json
import logging
import time
import threading
from typing import Dict, Any, Set, Optional
from datetime import datetime

import cv2
import numpy as np

from src.camera_streamer import get_camera_streamer
from src.audio_streamer import get_audio_streamer
from src.agents import (
    get_yolo_detector,
    get_pose_analyzer,
    get_movement_tracker,
    get_emotion_detector,
    get_face_mesh_analyzer,
    get_iris_tracker,
    get_audio_analyzer,
)
from src.config import get_settings

logger = logging.getLogger(__name__)


class DetectionBroadcaster:
    """
    Continuously runs detections on camera frames and broadcasts results.
    """
    
    def __init__(self, detection_interval: float = 1.0):
        """
        Initialize the detection broadcaster.
        
        Args:
            detection_interval: Seconds between detections (default: 1.0)
        """
        self.detection_interval = detection_interval
        self.settings = get_settings()
        
        # WebSocket clients
        self._clients: Set[Any] = set()
        self._clients_lock = asyncio.Lock()
        
        # Detection thread
        self._running = False
        self._detection_thread: Optional[threading.Thread] = None
        self._event_loop: Optional[asyncio.AbstractEventLoop] = None
        
        # Latest detection results (thread-safe)
        self._latest_results: Dict[str, Any] = {}
        self._results_lock = threading.Lock()
        
        logger.info(f"DetectionBroadcaster initialized (interval={detection_interval}s)")
    
    async def add_client(self, websocket):
        """Add a WebSocket client."""
        async with self._clients_lock:
            self._clients.add(websocket)
            client_count = len(self._clients)
            logger.info(f"Client connected (total: {client_count})")
            
            # Store event loop for cross-thread communication
            if self._event_loop is None:
                self._event_loop = asyncio.get_event_loop()
            
            # Start detection thread if this is the first client
            if client_count == 1 and not self._running:
                self._start_detection_thread()
    
    async def remove_client(self, websocket):
        """Remove a WebSocket client."""
        async with self._clients_lock:
            self._clients.discard(websocket)
            client_count = len(self._clients)
            logger.info(f"Client disconnected (total: {client_count})")
            
            # Stop detection thread if no clients remain
            if client_count == 0 and self._running:
                self._stop_detection_thread()
    
    def _start_detection_thread(self):
        """Start the detection thread."""
        if self._running:
            return
        
        self._running = True
        self._detection_thread = threading.Thread(
            target=self._detection_loop,
            daemon=True,
            name="DetectionBroadcaster"
        )
        self._detection_thread.start()
        logger.info("Detection thread started")
    
    def _stop_detection_thread(self):
        """Stop the detection thread."""
        if not self._running:
            return
        
        self._running = False
        if self._detection_thread:
            self._detection_thread.join(timeout=5.0)
        logger.info("Detection thread stopped")
    
    def _detection_loop(self):
        """Main detection loop (runs in background thread)."""
        logger.info("Detection loop started")
        
        streamer = get_camera_streamer()
        audio_streamer = get_audio_streamer()
        
        # Start audio capture when detection starts
        if self.settings.ENABLE_AUDIO_MONITORING:
            audio_streamer.add_viewer()
            logger.info("Audio monitoring enabled")
        
        while self._running:
            try:
                start_time = time.time()
                
                # Get latest frame
                frame_bytes = streamer.get_frame()
                
                if frame_bytes is None:
                    time.sleep(0.1)
                    continue
                
                # Decode frame
                frame_bgr = self._decode_frame(frame_bytes)
                if frame_bgr is None:
                    time.sleep(0.1)
                    continue
                
                # Run all detections
                results = self._run_detections(frame_bgr)
                
                # Store results (thread-safe)
                with self._results_lock:
                    self._latest_results = results
                
                # Broadcast to clients (schedule async task)
                if self._event_loop and not self._event_loop.is_closed():
                    asyncio.run_coroutine_threadsafe(
                        self._broadcast_results(results),
                        self._event_loop
                    )
                
                # Calculate processing time
                elapsed = time.time() - start_time
                logger.debug(f"Detection completed in {elapsed:.3f}s")
                
                # Wait for next interval
                sleep_time = max(0, self.detection_interval - elapsed)
                time.sleep(sleep_time)
            
            except Exception as e:
                logger.error(f"Error in detection loop: {e}", exc_info=True)
                time.sleep(1.0)
        
        # Stop audio capture when detection stops
        if self.settings.ENABLE_AUDIO_MONITORING:
            audio_streamer.remove_viewer()
            logger.info("Audio monitoring stopped")
        
        logger.info("Detection loop stopped")
    
    def _decode_frame(self, frame_bytes: bytes) -> Optional[np.ndarray]:
        """Decode JPEG frame bytes to OpenCV format."""
        try:
            np_buffer = np.frombuffer(frame_bytes, dtype=np.uint8)
            frame = cv2.imdecode(np_buffer, cv2.IMREAD_COLOR)
            return frame
        except Exception as e:
            logger.error(f"Error decoding frame: {e}")
            return None
    
    def _run_audio_analysis(self) -> Dict[str, Any]:
        """Run audio analysis on latest audio chunk."""
        try:
            audio_streamer = get_audio_streamer()
            audio_analyzer = get_audio_analyzer()
            
            # Check if audio is available
            if not audio_streamer.is_available():
                return {
                    "enabled": True,
                    "available": False,
                    "reason": "Audio device not available (sounddevice not installed or no microphone)"
                }
            
            # Get latest audio chunk
            audio_chunk = audio_streamer.get_latest_chunk()
            
            if audio_chunk is None:
                return {
                    "enabled": True,
                    "available": True,
                    "audio_detected": False,
                    "reason": "No audio data available yet"
                }
            
            # Analyze audio
            sample_rate = audio_streamer.get_sample_rate()
            analysis = audio_analyzer.analyze(audio_chunk, sample_rate)
            
            # Add enabled flag
            analysis["enabled"] = True
            analysis["available"] = True
            
            return analysis
        
        except Exception as e:
            logger.error(f"Error in audio analysis: {e}", exc_info=True)
            return {
                "enabled": True,
                "available": False,
                "error": str(e)
            }
    
    def _run_detections(self, frame_bgr: np.ndarray) -> Dict[str, Any]:
        """Run all detection agents on the frame."""
        timestamp = datetime.utcnow().isoformat()
        
        results = {
            "timestamp": timestamp,
            "frame_shape": list(frame_bgr.shape),
        }
        
        try:
            # 1. YOLO Detection
            yolo_detector = get_yolo_detector()
            yolo_result = yolo_detector.detect(frame_bgr)
            results["yolo"] = yolo_result
            
            # Determine focus region (baby > adult > full frame)
            focus_box = None
            person_detected = False
            baby_box = None
            baby_detected = False
            if isinstance(yolo_result, dict):
                baby_box = yolo_result.get("primary_baby_box")
                baby_detected = yolo_result.get("baby_detected", False)
                if baby_box:
                    focus_box = {"bbox": [
                        int(baby_box["bbox"][0]),
                        int(baby_box["bbox"][1]),
                        int(baby_box["bbox"][2]),
                        int(baby_box["bbox"][3]),
                    ]}
                    person_detected = True
                elif yolo_result.get("adult_boxes"):
                    adult_box = yolo_result["adult_boxes"][0]
                    focus_box = {"bbox": [
                        int(adult_box["bbox"][0]),
                        int(adult_box["bbox"][1]),
                        int(adult_box["bbox"][2]),
                        int(adult_box["bbox"][3]),
                    ]}
                    person_detected = True
            
            # 2. Pose Estimation
            pose_analyzer = get_pose_analyzer()
            pose_result = pose_analyzer.analyze(frame_bgr, focus_box=focus_box)
            results["pose"] = pose_result
            
            # 3. Movement Tracking
            movement_tracker = get_movement_tracker()
            movement_result = movement_tracker.analyze(frame_bgr)
            results["movement"] = movement_result
            
            # 4. Emotion Detection
            emotion_detector = get_emotion_detector()
            emotion_result = emotion_detector.infer(frame_bgr, baby_box=focus_box)
            results["emotion"] = emotion_result
            
            # 5. Face Mesh Analysis (always run - MediaPipe can detect faces even if YOLO misses person)
            if self.settings.ENABLE_FACE_MESH:
                face_mesh_analyzer = get_face_mesh_analyzer()
                face_mesh_result = face_mesh_analyzer.analyze(frame_bgr, focus_box=focus_box if person_detected else None)
                results["face_mesh"] = face_mesh_result
            else:
                results["face_mesh"] = {
                    "skipped": True,
                    "reason": "Face mesh disabled"
                }
            
            # 6. Iris Tracking (always run - MediaPipe can detect faces even if YOLO misses person)
            if self.settings.ENABLE_IRIS_TRACKING:
                iris_tracker = get_iris_tracker()
                iris_tracking_result = iris_tracker.analyze(frame_bgr, focus_box=focus_box if person_detected else None)
                results["iris_tracking"] = iris_tracking_result
            else:
                results["iris_tracking"] = {
                    "skipped": True,
                    "reason": "Iris tracking disabled"
                }
            
            # 7. Combined facial state (always build if face mesh/iris detect anything)
            results["combined_facial_state"] = self._build_combined_facial_state(
                results.get("emotion"),
                results.get("face_mesh"),
                results.get("iris_tracking")
            )
            
            # 8. Audio Analysis (if enabled)
            if self.settings.ENABLE_AUDIO_MONITORING:
                audio_result = self._run_audio_analysis()
                results["audio"] = audio_result
            else:
                results["audio"] = {
                    "enabled": False,
                    "reason": "Audio monitoring disabled in settings"
                }
            
            # 9. Overall summary
            results["summary"] = self._build_summary(results)
            
        except Exception as e:
            logger.error(f"Error running detections: {e}", exc_info=True)
            results["error"] = str(e)
        
        return results
    
    def _build_combined_facial_state(self, emotion_result, face_mesh_result, iris_result) -> Dict[str, Any]:
        """Build combined facial state from multiple sources."""
        combined = {"available": False}
        
        # Need at least one facial detection method
        has_iris = iris_result and isinstance(iris_result, dict) and iris_result.get("iris_detected")
        has_face_mesh = face_mesh_result and isinstance(face_mesh_result, dict) and face_mesh_result.get("face_detected")
        
        if not has_iris and not has_face_mesh:
            return combined
        
        combined["available"] = True
        
        # Store individual detection results
        if has_face_mesh:
            combined["eyes_mesh"] = face_mesh_result.get("eyes_state", "unknown")
            combined["eye_aspect_ratio"] = face_mesh_result.get("eye_aspect_ratio", {}).get("average", 0.0)
        
        if has_iris:
            combined["eyes_iris"] = iris_result.get("eyes_state", "unknown")
            combined["closure_pattern"] = iris_result.get("closure_pattern", "unknown")
            combined["eye_openness"] = iris_result.get("eye_openness", {}).get("average", 0.0)
        
        # Determine likely state (prioritize iris tracker's closure pattern as it's more accurate)
        if has_iris:
            closure_pattern = iris_result.get("closure_pattern", "unknown")
            if closure_pattern == "sleeping":
                combined["likely_state"] = "sleeping"
            elif closure_pattern == "drowsy":
                combined["likely_state"] = "drowsy"
            elif closure_pattern in ["awake", "blinking"]:
                combined["likely_state"] = "awake"
            else:
                # Fallback to raw eye state if closure pattern insufficient
                eye_state = iris_result.get("eyes_state", "unknown")
                if eye_state == "closed":
                    combined["likely_state"] = "sleeping"
                elif eye_state == "open":
                    combined["likely_state"] = "awake"
                else:
                    combined["likely_state"] = "drowsy"
        elif has_face_mesh:
            # Fallback to face mesh if iris not available
            eye_state = face_mesh_result.get("eyes_state", "unknown")
            if eye_state == "closed":
                combined["likely_state"] = "sleeping"
            elif eye_state == "open":
                combined["likely_state"] = "awake"
            else:
                combined["likely_state"] = "drowsy"
        else:
            combined["likely_state"] = "unknown"
        
        # Crying detection
        crying_indicators = []
        if emotion_result and isinstance(emotion_result, dict):
            if emotion_result.get("emotion_label") in ["crying", "distress", "pain"]:
                crying_indicators.append("emotion")
        
        if has_face_mesh:
            mar = face_mesh_result.get("mouth_aspect_ratio", 0.0)
            if mar > 0.6:
                crying_indicators.append("mouth_open")
        
        combined["crying_indicators"] = crying_indicators
        combined["likely_crying"] = len(crying_indicators) > 0
        
        # Face-down risk
        if has_face_mesh:
            combined["face_down_risk"] = face_mesh_result.get("face_down_detected", False)
        else:
            combined["face_down_risk"] = False
        
        return combined
    
    def _build_summary(self, results: Dict[str, Any]) -> Dict[str, Any]:
        """Build a concise summary of detection results."""
        summary = {}
        
        # YOLO summary
        yolo = results.get("yolo", {})
        summary["baby_detected"] = yolo.get("baby_detected", False)
        summary["adult_detected"] = yolo.get("adult_detected", False)
        summary["person_count"] = yolo.get("person_count", 0)
        
        # Pose summary
        pose = results.get("pose", {})
        summary["pose"] = pose.get("pose_label", "unknown")
        
        # Movement summary
        movement = results.get("movement", {})
        summary["movement"] = movement.get("movement_type", "unknown")
        summary["sudden_jerk"] = movement.get("sudden_jerk", False)
        
        # Emotion summary
        emotion = results.get("emotion", {})
        summary["emotion"] = emotion.get("emotion_label", "unknown")
        
        # Facial state summary
        combined = results.get("combined_facial_state", {})
        if combined.get("available"):
            summary["eyes_state"] = combined.get("likely_state", "unknown")
            summary["crying"] = combined.get("likely_crying", False)
            summary["face_down"] = combined.get("face_down_risk", False)
        
        # Audio summary
        audio = results.get("audio", {})
        if audio.get("enabled") and audio.get("available"):
            summary["audio_detected"] = audio.get("audio_detected", False)
            summary["audio_crying"] = audio.get("is_crying", False)
            summary["audio_awakening"] = audio.get("is_awakening", False)
            summary["audio_sound_type"] = audio.get("sound_type", "unknown")
            summary["audio_noise_level"] = audio.get("noise_level", -100.0)
        
        return summary
    
    async def _broadcast_results(self, results: Dict[str, Any]):
        """Broadcast detection results to all connected clients."""
        if not self._clients:
            return
        
        try:
            # Serialize results
            message = json.dumps(results, default=str)
            
            # Send to all clients
            async with self._clients_lock:
                disconnected = set()
                for client in self._clients:
                    try:
                        await client.send_text(message)
                    except Exception as e:
                        logger.warning(f"Failed to send to client: {e}")
                        disconnected.add(client)
                
                # Remove disconnected clients
                for client in disconnected:
                    self._clients.discard(client)
        
        except Exception as e:
            logger.error(f"Error broadcasting results: {e}", exc_info=True)
    
    def get_latest_results(self) -> Dict[str, Any]:
        """Get the latest detection results (thread-safe)."""
        with self._results_lock:
            return self._latest_results.copy()


# Global detection broadcaster instance
_broadcaster: Optional[DetectionBroadcaster] = None
_broadcaster_lock = threading.Lock()


def get_detection_broadcaster(detection_interval: float = 1.0) -> DetectionBroadcaster:
    """
    Get or create the global detection broadcaster instance.
    
    Args:
        detection_interval: Seconds between detections (default: 1.0)
    
    Returns:
        DetectionBroadcaster: The global broadcaster instance
    """
    global _broadcaster
    
    with _broadcaster_lock:
        if _broadcaster is None:
            _broadcaster = DetectionBroadcaster(detection_interval=detection_interval)
        
        return _broadcaster


def cleanup_detection_broadcaster():
    """Cleanup the global detection broadcaster."""
    global _broadcaster
    
    with _broadcaster_lock:
        if _broadcaster is not None:
            _broadcaster._stop_detection_thread()
            _broadcaster = None
