"""
Annotated video streamer with detection visualizations.

Draws pose skeletons, face mesh landmarks, bounding boxes, and labels
on video frames in real-time.
"""
import cv2
import numpy as np
import threading
import time
import logging
from typing import Optional, Dict, Any, Tuple, List
from dataclasses import dataclass

from src.camera_streamer import get_camera_streamer
from src.agents import (
    get_yolo_detector,
    get_pose_analyzer,
    get_emotion_detector,
    get_face_mesh_analyzer,
    get_iris_tracker,
)
from src.config import get_settings

logger = logging.getLogger(__name__)


# Color constants (BGR format for OpenCV)
COLOR_BABY_BOX = (0, 255, 255)  # Yellow
COLOR_ADULT_BOX = (0, 165, 255)  # Orange
COLOR_POSE_SKELETON = (0, 255, 0)  # Green
COLOR_FACE_MESH = (255, 0, 255)  # Magenta
COLOR_IRIS = (255, 255, 0)  # Cyan
COLOR_TEXT_BG = (0, 0, 0)  # Black
COLOR_TEXT = (255, 255, 255)  # White
COLOR_ALERT = (0, 0, 255)  # Red
COLOR_WARNING = (0, 165, 255)  # Orange
COLOR_SAFE = (0, 255, 0)  # Green


@dataclass
class VisualizationConfig:
    """Configuration for visualization elements."""
    draw_bboxes: bool = True
    draw_pose: bool = True
    draw_face_mesh: bool = True
    draw_iris: bool = True
    draw_labels: bool = True
    draw_status: bool = True
    
    # Styling
    bbox_thickness: int = 2
    pose_thickness: int = 2
    landmark_radius: int = 2
    text_scale: float = 0.6
    text_thickness: int = 2


class AnnotatedVideoStreamer:
    """
    Streams video with detection visualizations overlaid.
    """
    
    def __init__(self, fps: int = 10, config: Optional[VisualizationConfig] = None):
        """
        Initialize the annotated video streamer.
        
        Args:
            fps: Target frames per second for the annotated stream
            config: Visualization configuration
        """
        self.fps = fps
        self.frame_delay = 1.0 / fps if fps > 0 else 0.1
        self.config = config or VisualizationConfig()
        self.settings = get_settings()
        
        # Thread synchronization
        self._running = False
        self._thread: Optional[threading.Thread] = None
        self._lock = threading.Lock()
        
        # Latest annotated frame
        self._latest_frame: Optional[bytes] = None
        
        # Viewer tracking
        self._viewer_count = 0
        self._viewer_lock = threading.Lock()
        
        # Load agents
        self._yolo = None
        self._pose = None
        self._emotion = None
        self._face_mesh = None
        self._iris = None
        
        logger.info(f"AnnotatedVideoStreamer initialized (fps={fps})")
    
    def _load_agents(self):
        """Load detection agents (lazy loading)."""
        if self._yolo is None:
            self._yolo = get_yolo_detector()
            logger.info("YOLO detector loaded")
        
        if self._pose is None and self.settings.ENABLE_POSE_ESTIMATION:
            self._pose = get_pose_analyzer()
            logger.info("Pose analyzer loaded")
        
        if self._emotion is None and self.settings.ENABLE_EMOTION_DETECTION:
            self._emotion = get_emotion_detector()
            logger.info("Emotion detector loaded")
        
        if self._face_mesh is None and self.settings.ENABLE_FACE_MESH:
            self._face_mesh = get_face_mesh_analyzer()
            logger.info("Face mesh analyzer loaded")
        
        if self._iris is None and self.settings.ENABLE_IRIS_TRACKING:
            self._iris = get_iris_tracker()
            logger.info("Iris tracker loaded")
    
    def _draw_bounding_boxes(self, frame: np.ndarray, yolo_result: Dict[str, Any]):
        """Draw bounding boxes for detected babies and adults."""
        if not self.config.draw_bboxes:
            return
        
        # Draw baby box
        if yolo_result.get("baby_detected") and yolo_result.get("primary_baby_box"):
            box_data = yolo_result["primary_baby_box"]
            bbox = box_data["bbox"]
            # Ensure coordinates are integers
            x1, y1, x2, y2 = int(bbox[0]), int(bbox[1]), int(bbox[2]), int(bbox[3])
            confidence = box_data.get("confidence", 0.0)
            
            cv2.rectangle(frame, (x1, y1), (x2, y2), COLOR_BABY_BOX, self.config.bbox_thickness)
            
            # Add label
            label = f"Baby {confidence:.2f}"
            self._draw_label(frame, label, (x1, y1 - 10), COLOR_BABY_BOX)
        
        # Draw adult boxes
        if yolo_result.get("adult_boxes"):
            for box_data in yolo_result["adult_boxes"]:
                bbox = box_data["bbox"]
                # Ensure coordinates are integers
                x1, y1, x2, y2 = int(bbox[0]), int(bbox[1]), int(bbox[2]), int(bbox[3])
                confidence = box_data.get("confidence", 0.0)
                
                cv2.rectangle(frame, (x1, y1), (x2, y2), COLOR_ADULT_BOX, self.config.bbox_thickness)
                
                label = f"Adult {confidence:.2f}"
                self._draw_label(frame, label, (x1, y1 - 10), COLOR_ADULT_BOX)
    
    def _draw_pose_skeleton(self, frame: np.ndarray, pose_result: Dict[str, Any], focus_box: Optional[Dict[str, Any]] = None):
        """Draw pose estimation skeleton (like MediaPipe pose visualization)."""
        if not self.config.draw_pose or not pose_result.get("model_loaded"):
            return
        
        keypoints = pose_result.get("keypoints")
        if not keypoints or len(keypoints) == 0:
            return
        
        frame_h, frame_w = frame.shape[:2]
        offset_x = 0
        offset_y = 0
        if focus_box and "bbox" in focus_box:
            bbox = focus_box["bbox"]
            offset_x, offset_y = bbox[0], bbox[1]

        # MediaPipe Pose connections (same as in the reference images)
        # Format: (start_idx, end_idx)
        pose_connections = [
            # Face
            (0, 1), (1, 2), (2, 3), (3, 7),  # Right eye
            (0, 4), (4, 5), (5, 6), (6, 8),  # Left eye
            (9, 10),  # Mouth
            
            # Torso
            (11, 12),  # Shoulders
            (11, 23), (12, 24),  # Shoulder to hip
            (23, 24),  # Hips
            
            # Right arm
            (11, 13), (13, 15), (15, 17), (15, 19), (15, 21), (17, 19),
            
            # Left arm
            (12, 14), (14, 16), (16, 18), (16, 20), (16, 22), (18, 20),
            
            # Right leg
            (23, 25), (25, 27), (27, 29), (27, 31), (29, 31),
            
            # Left leg
            (24, 26), (26, 28), (28, 30), (28, 32), (30, 32),
        ]
        
        # Draw connections
        for start_idx, end_idx in pose_connections:
            if start_idx < len(keypoints) and end_idx < len(keypoints):
                start_kp = keypoints[start_idx]
                end_kp = keypoints[end_idx]
                
                # Check visibility
                if (start_kp.get("visibility", 0) > 0.1 and 
                    end_kp.get("visibility", 0) > 0.1):
                    
                    start_x = start_kp.get("x_px")
                    start_y = start_kp.get("y_px")
                    end_x = end_kp.get("x_px")
                    end_y = end_kp.get("y_px")

                    if start_x is None:
                        start_x = int(start_kp.get("x", 0) * frame_w) + offset_x
                    if start_y is None:
                        start_y = int(start_kp.get("y", 0) * frame_h) + offset_y
                    if end_x is None:
                        end_x = int(end_kp.get("x", 0) * frame_w) + offset_x
                    if end_y is None:
                        end_y = int(end_kp.get("y", 0) * frame_h) + offset_y
                    
                    cv2.line(frame, (start_x, start_y), (end_x, end_y), 
                            COLOR_POSE_SKELETON, self.config.pose_thickness)
        
        # Draw keypoints
        for kp in keypoints:
            if kp.get("visibility", 0) > 0.1:
                x = kp.get("x_px")
                y = kp.get("y_px")
                if x is None:
                    x = int(kp.get("x", 0) * frame_w) + offset_x
                if y is None:
                    y = int(kp.get("y", 0) * frame_h) + offset_y
                cv2.circle(frame, (x, y), self.config.landmark_radius + 1, 
                          COLOR_POSE_SKELETON, -1)
    
    def _draw_face_mesh(self, frame: np.ndarray, face_mesh_result: Dict[str, Any], focus_box: Optional[Dict[str, Any]] = None):
        """Draw face mesh landmarks."""
        if not self.config.draw_face_mesh or not face_mesh_result.get("face_detected"):
            return
        
        landmarks = face_mesh_result.get("landmarks_px")
        if not landmarks or len(landmarks) == 0:
            return
        
        # Draw subset of face mesh landmarks (all 468 would be too cluttered)
        # We'll draw:
        # - Face contour
        # - Eyes
        # - Eyebrows
        # - Nose
        # - Mouth
        
        # Key landmark indices (MediaPipe Face Mesh)
        face_contour = [10, 338, 297, 332, 284, 251, 389, 356, 454, 323, 361, 288,
                       397, 365, 379, 378, 400, 377, 152, 148, 176, 149, 150, 136,
                       172, 58, 132, 93, 234, 127, 162, 21, 54, 103, 67, 109]
        
        left_eye = [33, 246, 161, 160, 159, 158, 157, 173, 133, 155, 154, 153, 145, 144, 163, 7]
        right_eye = [263, 466, 388, 387, 386, 385, 384, 398, 362, 382, 381, 380, 374, 373, 390, 249]
        
        left_eyebrow = [46, 53, 52, 65, 55, 70, 63, 105, 66, 107]
        right_eyebrow = [276, 283, 282, 295, 285, 300, 293, 334, 296, 336]
        
        nose = [1, 2, 98, 327, 129, 358, 20, 240, 60, 79, 166, 237, 44, 274, 309, 392, 460]
        
        mouth = [0, 37, 39, 40, 185, 61, 146, 91, 181, 84, 17, 314, 405, 321, 375, 291, 267, 269, 270, 409]
        
        # Draw landmark sets
        landmark_sets = [
            (face_contour, COLOR_FACE_MESH, 1),
            (left_eye, (0, 255, 255), 1),  # Yellow for eyes
            (right_eye, (0, 255, 255), 1),
            (left_eyebrow, COLOR_FACE_MESH, 1),
            (right_eyebrow, COLOR_FACE_MESH, 1),
            (nose, COLOR_FACE_MESH, 1),
            (mouth, (0, 255, 128), 2),  # Green-yellow for mouth
        ]
        
        for indices, color, thickness in landmark_sets:
            for i in range(len(indices) - 1):
                start_idx = indices[i]
                end_idx = indices[i + 1]
                
                if start_idx < len(landmarks) and end_idx < len(landmarks):
                    start = landmarks[start_idx]
                    end = landmarks[end_idx]
                    
                    start_x = int(start["x"])
                    start_y = int(start["y"])
                    end_x = int(end["x"])
                    end_y = int(end["y"])
                    
                    cv2.line(frame, (start_x, start_y), (end_x, end_y), color, thickness)
    
    def _draw_iris_tracking(self, frame: np.ndarray, iris_result: Dict[str, Any], focus_box: Optional[Dict[str, Any]] = None):
        """Draw iris centers and gaze direction."""
        if not self.config.draw_iris or not iris_result.get("iris_detected"):
            return
        
        offset_x = 0
        offset_y = 0
        if focus_box and "bbox" in focus_box:
            bbox = focus_box["bbox"]
            offset_x, offset_y = bbox[0], bbox[1]
        
        # Draw left iris
        if iris_result.get("left_iris"):
            left_iris = iris_result["left_iris"]
            x = int(left_iris.get("x", 0))
            y = int(left_iris.get("y", 0))
            cv2.circle(frame, (x, y), 3, COLOR_IRIS, -1)
            cv2.circle(frame, (x, y), 8, COLOR_IRIS, 1)
        
        # Draw right iris
        if iris_result.get("right_iris"):
            right_iris = iris_result["right_iris"]
            x = int(right_iris.get("x", 0))
            y = int(right_iris.get("y", 0))
            cv2.circle(frame, (x, y), 3, COLOR_IRIS, -1)
            cv2.circle(frame, (x, y), 8, COLOR_IRIS, 1)
    
    def _draw_label(self, frame: np.ndarray, text: str, position: Tuple[int, int], color: Tuple[int, int, int]):
        """Draw text label with background."""
        if not self.config.draw_labels:
            return
        
        x, y = position
        
        # Get text size
        (text_w, text_h), baseline = cv2.getTextSize(
            text, cv2.FONT_HERSHEY_SIMPLEX, 
            self.config.text_scale, self.config.text_thickness
        )
        
        # Draw background rectangle
        padding = 5
        cv2.rectangle(frame, 
                     (x, y - text_h - padding), 
                     (x + text_w + padding, y + padding),
                     COLOR_TEXT_BG, -1)
        
        # Draw text
        cv2.putText(frame, text, (x, y), 
                   cv2.FONT_HERSHEY_SIMPLEX, 
                   self.config.text_scale, color, 
                   self.config.text_thickness)
    
    def _draw_status_overlay(self, frame: np.ndarray, detections: Dict[str, Any]):
        """Draw status overlay with detection summary."""
        if not self.config.draw_status:
            return
        
        summary = detections.get("summary", {})
        combined_facial = detections.get("combined_facial_state", {})
        
        # Determine overall status color
        if summary.get("face_down") or summary.get("sudden_jerk"):
            status_color = COLOR_ALERT
            status_text = "🚨 ALERT"
        elif summary.get("crying"):
            status_color = COLOR_WARNING
            status_text = "⚠️ CRYING"
        elif combined_facial.get("likely_state") == "sleeping":
            status_color = COLOR_SAFE
            status_text = "✓ SLEEPING"
        elif combined_facial.get("likely_state") == "awake":
            status_color = (0, 255, 255)  # Yellow
            status_text = "👁 AWAKE"
        else:
            status_color = COLOR_SAFE
            status_text = "✓ MONITORING"
        
        # Draw status bar at the top
        height, width = frame.shape[:2]
        bar_height = 60
        
        # Draw semi-transparent overlay
        overlay = frame.copy()
        cv2.rectangle(overlay, (0, 0), (width, bar_height), (0, 0, 0), -1)
        cv2.addWeighted(overlay, 0.6, frame, 0.4, 0, frame)
        
        # Draw status text
        self._draw_label(frame, status_text, (10, 25), status_color)
        
        # Draw additional info
        info_items = []
        
        # Show detection info regardless of YOLO baby detection
        # If face mesh or iris detected faces, show that info
        yolo_info = detections.get("yolo", {})
        if summary.get("baby_detected"):
            info_items.append("👶 Baby")
        elif yolo_info.get("adult_detected"):
            info_items.append("👤 Person")
        elif detections.get("face_mesh", {}).get("face_detected") or detections.get("iris_tracking", {}).get("face_detected"):
            info_items.append("👤 Face")
        else:
            info_items.append("❌ No face")
        
        # Always show detection results if available
        if summary.get('pose') != 'unknown':
            info_items.append(f"Pose: {summary.get('pose', 'unknown')}")
        if summary.get('emotion') != 'unknown':
            info_items.append(f"Emotion: {summary.get('emotion', 'unknown')}")
        if summary.get('eyes_state') != 'unknown':
            info_items.append(f"Eyes: {summary.get('eyes_state', 'unknown')}")
        
        x_offset = 200
        for item in info_items:
            self._draw_label(frame, item, (x_offset, 25), COLOR_TEXT)
            x_offset += 200
    
    def _run_detections_and_annotate(self, frame_bgr: np.ndarray) -> np.ndarray:
        """Run all detections and annotate the frame."""
        # Ensure agents are loaded
        self._load_agents()
        
        # Initialize detection results
        detections = {
            "summary": {
                "baby_detected": False,
                "pose": "unknown",
                "emotion": "unknown",
                "eyes_state": "unknown",
                "crying": False,
                "face_down": False,
                "sudden_jerk": False,
            }
        }
        
        try:
            # 1. YOLO Detection
            yolo_result = self._yolo.detect(frame_bgr)
            detections["yolo"] = yolo_result
            detections["summary"]["baby_detected"] = yolo_result.get("baby_detected", False)
            
            # Draw bounding boxes
            self._draw_bounding_boxes(frame_bgr, yolo_result)
            
            # Get focus box from ANY detected person (baby OR adult)
            # Priority: baby > adult > None (whole frame)
            focus_box = None
            person_detected = False
            
            # Try baby first
            if yolo_result.get("primary_baby_box"):
                bbox = yolo_result["primary_baby_box"]["bbox"]
                # Agents expect focus_box as dict with "bbox" key
                focus_box = {"bbox": [int(bbox[0]), int(bbox[1]), int(bbox[2]), int(bbox[3])]}
                person_detected = True
                logger.debug("Using baby bounding box for detections")
            
            # Fall back to adult if no baby detected
            elif yolo_result.get("adult_boxes") and len(yolo_result["adult_boxes"]) > 0:
                bbox = yolo_result["adult_boxes"][0]["bbox"]  # Use first adult detected
                # Agents expect focus_box as dict with "bbox" key
                focus_box = {"bbox": [int(bbox[0]), int(bbox[1]), int(bbox[2]), int(bbox[3])]}
                person_detected = True
                logger.debug("Using adult bounding box for detections (no baby detected)")
            
            # If no person detected by YOLO, still run detections on whole frame
            # MediaPipe can detect faces even if YOLO missed the person
            else:
                logger.debug("No person detected by YOLO, running detections on whole frame")
                person_detected = False  # Will use None as focus_box (whole frame)
            
            # 2. Pose Estimation
            if self._pose:
                try:
                    pose_result = self._pose.analyze(frame_bgr, focus_box)
                    detections["pose"] = pose_result
                    detections["summary"]["pose"] = pose_result.get("pose_label", "unknown")
                    
                    # Draw pose skeleton
                    self._draw_pose_skeleton(frame_bgr, pose_result, focus_box)
                except Exception as e:
                    logger.error(f"Pose estimation error: {e}")
            
            # 3. Emotion Detection
            if self._emotion:
                try:
                    # EmotionDetector uses infer() not analyze()
                    # focus_box is already in the correct format
                    emotion_result = self._emotion.infer(frame_bgr, focus_box)
                    detections["emotion"] = emotion_result
                    detections["summary"]["emotion"] = emotion_result.get("emotion_label", "unknown")
                    
                    # Check for crying
                    if emotion_result.get("emotion_label") in ["crying", "pain", "distress"]:
                        detections["summary"]["crying"] = True
                except Exception as e:
                    logger.error(f"Emotion detection error: {e}")
            
            # 4. Face Mesh
            if self._face_mesh:
                try:
                    face_mesh_result = self._face_mesh.analyze(frame_bgr, focus_box)
                    if (not face_mesh_result.get("face_detected")) and focus_box:
                        face_mesh_result = self._face_mesh.analyze(frame_bgr, None)
                    detections["face_mesh"] = face_mesh_result
                    detections["summary"]["eyes_state"] = face_mesh_result.get("eyes_state", "unknown")
                    detections["summary"]["face_down"] = face_mesh_result.get("face_down_detected", False)
                    
                    # Draw face mesh
                    self._draw_face_mesh(frame_bgr, face_mesh_result, focus_box)
                except Exception as e:
                    logger.error(f"Face mesh error: {e}")
            
            # 5. Iris Tracking
            if self._iris:
                try:
                    iris_result = self._iris.analyze(frame_bgr, focus_box)
                    if (not iris_result.get("iris_detected")) and focus_box:
                        iris_result = self._iris.analyze(frame_bgr, None)
                    detections["iris_tracking"] = iris_result
                    
                    # Draw iris tracking
                    self._draw_iris_tracking(frame_bgr, iris_result, focus_box)
                    
                    # Build combined facial state
                    detections["combined_facial_state"] = self._build_combined_facial_state(
                        detections.get("emotion"),
                        detections.get("face_mesh"),
                        iris_result
                    )
                except Exception as e:
                    logger.error(f"Iris tracking error: {e}")
            
            # Draw status overlay
            self._draw_status_overlay(frame_bgr, detections)
            
        except Exception as e:
            logger.error(f"Error during detection and annotation: {e}")
        
        return frame_bgr
    
    def _build_combined_facial_state(self, emotion_result: Optional[Dict], 
                                     face_mesh_result: Optional[Dict], 
                                     iris_result: Optional[Dict]) -> Dict[str, Any]:
        """Build combined facial state from all facial detections."""
        state = {
            "available": False,
            "likely_state": "unknown",
            "crying_indicators": [],
            "likely_crying": False,
            "face_down_risk": False,
        }
        
        if not face_mesh_result or not iris_result:
            return state
        
        state["available"] = True
        state["eyes_mesh"] = face_mesh_result.get("eyes_state", "unknown")
        state["eyes_iris"] = iris_result.get("eyes_state", "unknown")
        state["closure_pattern"] = iris_result.get("closure_pattern", "unknown")
        
        # Determine likely state
        if iris_result.get("closure_pattern") == "sleeping":
            state["likely_state"] = "sleeping"
        elif iris_result.get("closure_pattern") == "drowsy":
            state["likely_state"] = "drowsy"
        else:
            state["likely_state"] = "awake"
        
        # Check crying indicators
        if emotion_result:
            emotion = emotion_result.get("emotion_label", "")
            if emotion in ["crying", "pain", "distress"]:
                state["crying_indicators"].append(f"emotion_{emotion}")
        
        if face_mesh_result:
            mar = face_mesh_result.get("mouth_aspect_ratio", 0)
            if mar > 0.6:
                state["crying_indicators"].append("mouth_wide_open")
        
        state["likely_crying"] = len(state["crying_indicators"]) > 0
        
        # Face-down risk
        state["face_down_risk"] = face_mesh_result.get("face_down_detected", False)
        
        return state
    
    def _annotation_loop(self):
        """Main loop for annotating frames."""
        logger.info("Annotation loop started")
        camera_streamer = get_camera_streamer()
        camera_streamer.add_viewer()
        # Give the underlying camera a moment to produce frames
        time.sleep(0.1)
        
        try:
            while self._running:
                try:
                    # Get latest frame from camera
                    frame_bytes = camera_streamer.get_frame()
                    
                    if frame_bytes is None:
                        time.sleep(0.1)
                        continue
                    
                    # Decode frame
                    nparr = np.frombuffer(frame_bytes, np.uint8)
                    frame = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
                    
                    if frame is None:
                        continue
                    
                    # Run detections and annotate
                    annotated_frame = self._run_detections_and_annotate(frame)
                    
                    # Encode annotated frame
                    encode_params = [cv2.IMWRITE_JPEG_QUALITY, 85]
                    success, buffer = cv2.imencode('.jpg', annotated_frame, encode_params)
                    
                    if success:
                        with self._lock:
                            self._latest_frame = buffer.tobytes()
                    
                    # Control frame rate
                    time.sleep(self.frame_delay)
                
                except Exception as e:
                    logger.error(f"Error in annotation loop: {e}")
                    time.sleep(0.5)
        finally:
            camera_streamer.remove_viewer()
            logger.info("Annotation loop stopped")
    
    def start(self):
        """Start the annotated video streamer."""
        with self._lock:
            if self._running:
                logger.warning("Annotated streamer already running")
                return
            
            self._running = True
            self._thread = threading.Thread(target=self._annotation_loop, daemon=True)
            self._thread.start()
            logger.info("Annotated video streamer started")
    
    def stop(self):
        """Stop the annotated video streamer."""
        with self._lock:
            if not self._running:
                return
            
            self._running = False
        
        if self._thread is not None:
            self._thread.join(timeout=5.0)
        
        logger.info("Annotated video streamer stopped")
    
    def add_viewer(self):
        """Register a new viewer."""
        with self._viewer_lock:
            self._viewer_count += 1
            if self._viewer_count == 1:
                self.start()
            logger.info(f"Viewer added to annotated stream (total: {self._viewer_count})")
    
    def remove_viewer(self):
        """Unregister a viewer."""
        with self._viewer_lock:
            if self._viewer_count > 0:
                self._viewer_count -= 1
                logger.info(f"Viewer removed from annotated stream (total: {self._viewer_count})")
                
                if self._viewer_count == 0:
                    self.stop()
    
    def get_frame(self) -> Optional[bytes]:
        """Get the latest annotated frame."""
        with self._lock:
            return self._latest_frame
    
    def is_available(self) -> bool:
        """Check if annotated stream is available."""
        with self._lock:
            return self._running and self._latest_frame is not None


# Global annotated streamer instance
_annotated_streamer: Optional[AnnotatedVideoStreamer] = None
_streamer_lock = threading.Lock()


def get_annotated_streamer() -> AnnotatedVideoStreamer:
    """Get or create the global annotated video streamer instance."""
    global _annotated_streamer
    
    with _streamer_lock:
        if _annotated_streamer is None:
            _annotated_streamer = AnnotatedVideoStreamer(fps=10)
        
        return _annotated_streamer


def cleanup_annotated_streamer():
    """Cleanup the global annotated streamer."""
    global _annotated_streamer
    
    with _streamer_lock:
        if _annotated_streamer is not None:
            _annotated_streamer.stop()
            _annotated_streamer = None
