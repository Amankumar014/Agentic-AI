"""
Iris Tracking agent powered by MediaPipe Iris.

Extracts:
- Precise iris landmarks (5 landmarks per eye)
- Eye openness score
- Gaze direction
- Blinking frequency
- Eye-closure patterns to support sleep detection
"""
from __future__ import annotations

import threading
import time
from collections import deque
from typing import Any, Dict, List, Optional

import cv2
import numpy as np

try:
    import mediapipe as mp  # type: ignore
except Exception:  # pragma: no cover - optional dependency
    mp = None


class IrisTracker:
    """MediaPipe Iris tracker for precise eye and gaze analysis."""

    def __init__(self) -> None:
        if mp is None:
            self._face_mesh = None
            return

        # Use Face Mesh with iris landmarks enabled
        self._face_mesh = mp.solutions.face_mesh.FaceMesh(
            static_image_mode=True,
            max_num_faces=1,
            refine_landmarks=True,  # This enables iris landmarks
            min_detection_confidence=0.5,
            min_tracking_confidence=0.5,
        )
        self._mp_face_mesh = mp.solutions.face_mesh
        
        # Track blink history for frequency calculation
        self._blink_history: deque = deque(maxlen=30)  # Last 30 frames (~2 seconds at 15fps)
        self._last_blink_time: Optional[float] = None
        self._blink_counter = 0

    def close(self) -> None:
        if self._face_mesh is not None:
            self._face_mesh.close()

    def analyze(
        self,
        frame_bgr: np.ndarray,
        focus_box: Optional[Dict[str, float]] = None,
    ) -> Dict[str, Any]:
        """
        Analyze iris and eye state from frame.
        
        Args:
            frame_bgr: BGR image array
            focus_box: Optional bounding box to focus on (from YOLO baby detection)
            
        Returns:
            Dict containing iris tracking analysis results
        """
        if mp is None or self._face_mesh is None:
            return {
                "error": "mediapipe not installed - run `pip install mediapipe`",
                "model_loaded": False,
            }

        # Extract ROI if focus box provided
        roi = frame_bgr
        offset_x, offset_y = 0, 0
        if focus_box and "bbox" in focus_box:
            x1, y1, x2, y2 = (
                int(focus_box["bbox"][0]),
                int(focus_box["bbox"][1]),
                int(focus_box["bbox"][2]),
                int(focus_box["bbox"][3]),
            )
            # Add padding
            x1 = max(x1 - 20, 0)
            y1 = max(y1 - 20, 0)
            x2 = min(x2 + 20, frame_bgr.shape[1] - 1)
            y2 = min(y2 + 20, frame_bgr.shape[0] - 1)
            roi = frame_bgr[y1:y2, x1:x2]
            offset_x, offset_y = x1, y1
            if roi.size == 0:
                roi = frame_bgr
                offset_x, offset_y = 0, 0

        roi_h, roi_w = roi.shape[:2]

        # Process with MediaPipe
        frame_rgb = cv2.cvtColor(roi, cv2.COLOR_BGR2RGB)
        result = self._face_mesh.process(frame_rgb)

        if not result.multi_face_landmarks:
            return {
                "model_loaded": True,
                "face_detected": False,
                "iris_detected": False,
                "reason": "No face landmarks detected",
            }

        # Extract first face
        face_landmarks = result.multi_face_landmarks[0]
        landmarks = face_landmarks.landmark

        # Extract iris landmarks
        # Left iris: 468-472 (center at 468)
        # Right iris: 473-477 (center at 473)
        left_iris_center = landmarks[468] if len(landmarks) > 468 else None
        right_iris_center = landmarks[473] if len(landmarks) > 473 else None

        if left_iris_center is None or right_iris_center is None:
            return {
                "model_loaded": True,
                "face_detected": True,
                "iris_detected": False,
                "reason": "Iris landmarks not available",
            }

        # Get eye corners for calculating eye openness
        left_eye_left = landmarks[33]
        left_eye_right = landmarks[133]
        right_eye_left = landmarks[362]
        right_eye_right = landmarks[263]

        # Calculate eye openness (vertical eye opening)
        left_eye_openness = self._calculate_eye_openness(landmarks, is_left=True)
        right_eye_openness = self._calculate_eye_openness(landmarks, is_left=False)
        avg_eye_openness = (left_eye_openness + right_eye_openness) / 2.0

        # Gaze direction (iris position relative to eye center)
        left_gaze = self._calculate_gaze_direction(
            left_iris_center, left_eye_left, left_eye_right
        )
        right_gaze = self._calculate_gaze_direction(
            right_iris_center, right_eye_left, right_eye_right
        )

        # Determine if eyes are closed/open
        # Adjusted thresholds for better detection:
        # - Eyes are considered closed if openness < 0.20 (was 0.15)
        # - Eyes are considered open if openness > 0.30 (was 0.22)
        # - Between 0.20-0.30 is partially_open
        eyes_closed = avg_eye_openness < 0.30
        eyes_open = avg_eye_openness > 0.40
        
        # Track blink events
        current_time = time.time()
        self._blink_history.append(eyes_closed)
        
        # Detect blink transition (was open, now closed)
        if eyes_closed and len(self._blink_history) > 1 and not self._blink_history[-2]:
            self._blink_counter += 1
            self._last_blink_time = current_time

        # Calculate blink frequency (blinks per minute)
        blink_frequency = self._calculate_blink_frequency()

        # Eye closure pattern (for sleep detection)
        closure_pattern = self._analyze_closure_pattern()

        # Micro movements (iris position changes - simplified for now)
        iris_movement_detected = abs(left_gaze["horizontal"]) > 0.3 or abs(right_gaze["horizontal"]) > 0.3

        left_iris_x = int(left_iris_center.x * roi_w) + offset_x
        left_iris_y = int(left_iris_center.y * roi_h) + offset_y
        right_iris_x = int(right_iris_center.x * roi_w) + offset_x
        right_iris_y = int(right_iris_center.y * roi_h) + offset_y
        
        # Debug logging for eye state detection
        import logging
        logger = logging.getLogger(__name__)
        logger.debug(f"Iris: openness={avg_eye_openness:.3f}, eyes={('open' if eyes_open else ('closed' if eyes_closed else 'partial'))}, pattern={closure_pattern}")

        return {
            "model_loaded": True,
            "face_detected": True,
            "iris_detected": True,
            "left_iris": {
                "x_norm": round(left_iris_center.x, 4),
                "y_norm": round(left_iris_center.y, 4),
                "x": left_iris_x,
                "y": left_iris_y,
                "z": round(left_iris_center.z, 4),
            },
            "right_iris": {
                "x_norm": round(right_iris_center.x, 4),
                "y_norm": round(right_iris_center.y, 4),
                "x": right_iris_x,
                "y": right_iris_y,
                "z": round(right_iris_center.z, 4),
            },
            "eye_openness": {
                "left": round(left_eye_openness, 4),
                "right": round(right_eye_openness, 4),
                "average": round(avg_eye_openness, 4),
            },
            "gaze_direction": {
                "left": left_gaze,
                "right": right_gaze,
            },
            "eyes_state": "closed" if eyes_closed else ("open" if eyes_open else "partially_open"),
            "blinking": {
                "frequency_per_minute": round(blink_frequency, 2),
                "last_blink_seconds_ago": round(current_time - self._last_blink_time, 2) if self._last_blink_time else None,
                "total_blinks": self._blink_counter,
            },
            "closure_pattern": closure_pattern,
            "iris_movement_detected": iris_movement_detected,
        }

    def _calculate_eye_openness(self, landmarks, is_left: bool) -> float:
        """
        Calculate eye openness score (0 = closed, 1 = wide open).
        
        Uses vertical distance between upper and lower eyelid.
        """
        if is_left:
            # Left eye: top (159), bottom (145), left (33), right (133)
            top = landmarks[159]
            bottom = landmarks[145]
            left = landmarks[33]
            right = landmarks[133]
        else:
            # Right eye: top (386), bottom (374), left (362), right (263)
            top = landmarks[386]
            bottom = landmarks[374]
            left = landmarks[362]
            right = landmarks[263]

        def euclidean_distance(pt1, pt2):
            return np.sqrt((pt1.x - pt2.x)**2 + (pt1.y - pt2.y)**2)

        # Vertical distance (eye height)
        eye_height = euclidean_distance(top, bottom)
        
        # Horizontal distance (eye width for normalization)
        eye_width = euclidean_distance(left, right)

        if eye_width < 1e-6:
            return 0.0
        
        # Normalize by eye width
        openness = eye_height / eye_width
        return openness

    def _calculate_gaze_direction(self, iris, eye_left, eye_right) -> Dict[str, float]:
        """
        Calculate gaze direction based on iris position relative to eye corners.
        
        Returns horizontal and vertical gaze components.
        -1 (left/up) to +1 (right/down)
        """
        # Calculate eye center
        eye_center_x = (eye_left.x + eye_right.x) / 2.0
        eye_center_y = (eye_left.y + eye_right.y) / 2.0
        
        # Calculate eye width/height for normalization
        eye_width = abs(eye_right.x - eye_left.x)
        
        if eye_width < 1e-6:
            return {"horizontal": 0.0, "vertical": 0.0}
        
        # Iris offset from center (normalized)
        horizontal_offset = (iris.x - eye_center_x) / eye_width
        vertical_offset = (iris.y - eye_center_y) / eye_width
        
        # Clamp to reasonable range
        horizontal_offset = max(-1.0, min(1.0, horizontal_offset * 3))
        vertical_offset = max(-1.0, min(1.0, vertical_offset * 3))
        
        return {
            "horizontal": round(float(horizontal_offset), 3),
            "vertical": round(float(vertical_offset), 3),
        }

    def _calculate_blink_frequency(self) -> float:
        """
        Calculate blink frequency (blinks per minute) based on recent history.
        """
        if len(self._blink_history) < 2:
            return 0.0
        
        # Count blink transitions in recent history
        blinks = 0
        for i in range(1, len(self._blink_history)):
            # Transition from open to closed
            if self._blink_history[i] and not self._blink_history[i-1]:
                blinks += 1
        
        # Estimate frames as seconds (assuming ~15 fps)
        duration_seconds = len(self._blink_history) / 15.0
        if duration_seconds < 0.1:
            return 0.0
        
        # Convert to per minute
        blinks_per_minute = (blinks / duration_seconds) * 60.0
        return blinks_per_minute

    def _analyze_closure_pattern(self) -> str:
        """
        Analyze eye closure pattern for sleep detection.
        
        Returns pattern type: 'awake', 'drowsy', 'sleeping', 'blinking'
        """
        if len(self._blink_history) < 5:
            return "insufficient_data"
        
        # Count closed frames in recent history
        closed_count = sum(self._blink_history)
        total_count = len(self._blink_history)
        closed_ratio = closed_count / total_count
        
        # Determine pattern
        if closed_ratio > 0.8:
            return "sleeping"  # Eyes closed most of the time
        elif closed_ratio > 0.5:
            return "drowsy"    # Eyes closed more than half the time
        elif closed_ratio > 0.1:
            return "blinking"  # Some blinks detected
        else:
            return "awake"     # Eyes mostly open

    def reset_history(self) -> None:
        """Reset blink tracking history. Useful when starting new monitoring session."""
        self._blink_history.clear()
        self._blink_counter = 0
        self._last_blink_time = None


_IRIS_TRACKER: Optional[IrisTracker] = None
_IRIS_TRACKER_LOCK = threading.Lock()


def get_iris_tracker() -> IrisTracker:
    """Return singleton iris tracker."""
    global _IRIS_TRACKER
    if _IRIS_TRACKER is None:
        with _IRIS_TRACKER_LOCK:
            if _IRIS_TRACKER is None:
                _IRIS_TRACKER = IrisTracker()
    return _IRIS_TRACKER
