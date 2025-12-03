"""
Face Mesh detection agent powered by MediaPipe Face Mesh.

Extracts:
- 468 face landmarks
- Eye aspect ratios (EAR)
- Mouth aspect ratios (MAR)
- Head orientation (pitch, yaw, roll)
- Nose bridge movement for breathing analysis
- Face visibility and face-down detection
"""
from __future__ import annotations

import threading
from typing import Any, Dict, List, Optional

import cv2
import numpy as np

try:
    import mediapipe as mp  # type: ignore
except Exception:  # pragma: no cover - optional dependency
    mp = None


class FaceMeshAnalyzer:
    """MediaPipe Face Mesh analyzer for detailed facial state detection."""

    def __init__(self) -> None:
        if mp is None:
            self._face_mesh = None
            return

        self._face_mesh = mp.solutions.face_mesh.FaceMesh(
            static_image_mode=True,
            max_num_faces=1,
            refine_landmarks=True,
            min_detection_confidence=0.5,
            min_tracking_confidence=0.5,
        )
        self._mp_face_mesh = mp.solutions.face_mesh

    def close(self) -> None:
        if self._face_mesh is not None:
            self._face_mesh.close()

    def analyze(
        self,
        frame_bgr: np.ndarray,
        focus_box: Optional[Dict[str, float]] = None,
    ) -> Dict[str, Any]:
        """
        Analyze face mesh from frame.
        
        Args:
            frame_bgr: BGR image array
            focus_box: Optional bounding box to focus on (from YOLO baby detection)
            
        Returns:
            Dict containing face mesh analysis results
        """
        if mp is None or self._face_mesh is None:
            return {
                "error": "mediapipe not installed - run `pip install mediapipe`",
                "model_loaded": False,
            }

        # Extract ROI if focus box provided
        roi = frame_bgr
        offset_x, offset_y = 0, 0
        if focus_box:
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

        # Process with MediaPipe
        frame_rgb = cv2.cvtColor(roi, cv2.COLOR_BGR2RGB)
        result = self._face_mesh.process(frame_rgb)

        if not result.multi_face_landmarks:
            return {
                "model_loaded": True,
                "face_detected": False,
                "landmarks_count": 0,
                "reason": "No face landmarks detected",
            }

        # Extract first face (baby should be primary face)
        face_landmarks = result.multi_face_landmarks[0]
        landmarks = face_landmarks.landmark

        # Convert landmarks to pixel coordinates
        h, w = roi.shape[:2]
        landmarks_3d = []
        landmarks_px = []
        for lm in landmarks:
            x_px = int(lm.x * w) + offset_x
            y_px = int(lm.y * h) + offset_y
            z = lm.z
            landmarks_3d.append({"x": lm.x, "y": lm.y, "z": z, "visibility": getattr(lm, 'visibility', 1.0)})
            landmarks_px.append({"x": x_px, "y": y_px})

        # Calculate eye aspect ratios (EAR)
        left_ear = self._calculate_eye_aspect_ratio(landmarks, is_left=True)
        right_ear = self._calculate_eye_aspect_ratio(landmarks, is_left=False)
        avg_ear = (left_ear + right_ear) / 2.0

        # Calculate mouth aspect ratio (MAR)
        mar = self._calculate_mouth_aspect_ratio(landmarks)

        # Calculate head orientation (pitch, yaw, roll)
        head_orientation = self._calculate_head_orientation(landmarks_px, frame_bgr.shape[1], frame_bgr.shape[0])

        # Nose bridge movement for breathing (compare against previous frame if available)
        nose_bridge_y = landmarks[6].y  # Nose tip normalized y-coordinate
        
        # Face visibility check
        visibility_score = self._calculate_face_visibility(landmarks)
        face_down = self._detect_face_down(landmarks)

        # Determine eye state
        # Adjusted thresholds for better detection:
        # - Eyes are considered closed if EAR < 0.20 (was 0.18)
        # - Eyes are considered open if EAR > 0.28 (was 0.25)
        # - Between 0.20-0.28 is partially_open
        eyes_closed = avg_ear < 0.30  # Threshold for closed eyes
        eyes_open = avg_ear > 0.33
        mouth_open = mar > 0.5

        return {
            "model_loaded": True,
            "face_detected": True,
            "landmarks_count": len(landmarks),
            "landmarks_3d": landmarks_3d[:10],  # First 10 for brevity in logs
            "landmarks_px": landmarks_px,
            "eye_aspect_ratio": {
                "left": round(left_ear, 4),
                "right": round(right_ear, 4),
                "average": round(avg_ear, 4),
            },
            "mouth_aspect_ratio": round(mar, 4),
            "head_orientation": head_orientation,
            "nose_bridge_y": round(nose_bridge_y, 4),
            "face_visibility_score": round(visibility_score, 4),
            "face_down_detected": face_down,
            "eyes_state": "closed" if eyes_closed else ("open" if eyes_open else "partially_open"),
            "mouth_state": "open" if mouth_open else "closed",
        }

    def _calculate_eye_aspect_ratio(self, landmarks, is_left: bool) -> float:
        """
        Calculate Eye Aspect Ratio (EAR) for blink detection.
        
        EAR = (||p2 - p6|| + ||p3 - p5||) / (2 * ||p1 - p4||)
        
        Left eye landmarks: 33, 160, 158, 133, 153, 144
        Right eye landmarks: 362, 385, 387, 263, 373, 380
        """
        if is_left:
            # Left eye indices
            p1, p2, p3, p4, p5, p6 = 33, 160, 158, 133, 153, 144
        else:
            # Right eye indices
            p1, p2, p3, p4, p5, p6 = 362, 385, 387, 263, 373, 380

        def euclidean_distance(pt1, pt2):
            return np.sqrt((pt1.x - pt2.x)**2 + (pt1.y - pt2.y)**2)

        # Vertical distances
        v1 = euclidean_distance(landmarks[p2], landmarks[p6])
        v2 = euclidean_distance(landmarks[p3], landmarks[p5])
        
        # Horizontal distance
        h = euclidean_distance(landmarks[p1], landmarks[p4])

        if h < 1e-6:
            return 0.0
        
        ear = (v1 + v2) / (2.0 * h)
        return ear

    def _calculate_mouth_aspect_ratio(self, landmarks) -> float:
        """
        Calculate Mouth Aspect Ratio (MAR) for mouth open detection.
        
        Upper lip: 13
        Lower lip: 14
        Left mouth corner: 78
        Right mouth corner: 308
        """
        upper_lip = landmarks[13]
        lower_lip = landmarks[14]
        left_corner = landmarks[78]
        right_corner = landmarks[308]

        def euclidean_distance(pt1, pt2):
            return np.sqrt((pt1.x - pt2.x)**2 + (pt1.y - pt2.y)**2)

        # Vertical distance (mouth height)
        mouth_height = euclidean_distance(upper_lip, lower_lip)
        
        # Horizontal distance (mouth width)
        mouth_width = euclidean_distance(left_corner, right_corner)

        if mouth_width < 1e-6:
            return 0.0
        
        mar = mouth_height / mouth_width
        return mar

    def _calculate_head_orientation(self, landmarks_px: List[Dict[str, int]], width: int, height: int) -> Dict[str, float]:
        """
        Calculate head orientation (pitch, yaw, roll) using facial landmarks.
        
        Uses nose tip, chin, left eye, right eye, left mouth, right mouth.
        """
        # 3D model points (generic face model)
        model_points = np.array([
            (0.0, 0.0, 0.0),             # Nose tip
            (0.0, -330.0, -65.0),        # Chin
            (-225.0, 170.0, -135.0),     # Left eye left corner
            (225.0, 170.0, -135.0),      # Right eye right corner
            (-150.0, -150.0, -125.0),    # Left mouth corner
            (150.0, -150.0, -125.0)      # Right mouth corner
        ], dtype=np.float64)

        # 2D image points from landmarks
        # Indices: nose tip (1), chin (152), left eye (33), right eye (263), left mouth (61), right mouth (291)
        try:
            image_points = np.array([
                [landmarks_px[1]["x"], landmarks_px[1]["y"]],    # Nose tip
                [landmarks_px[152]["x"], landmarks_px[152]["y"]],  # Chin
                [landmarks_px[33]["x"], landmarks_px[33]["y"]],   # Left eye
                [landmarks_px[263]["x"], landmarks_px[263]["y"]],  # Right eye
                [landmarks_px[61]["x"], landmarks_px[61]["y"]],   # Left mouth
                [landmarks_px[291]["x"], landmarks_px[291]["y"]],  # Right mouth
            ], dtype=np.float64)
        except Exception:
            return {"pitch": 0.0, "yaw": 0.0, "roll": 0.0, "error": "insufficient landmarks"}

        # Camera matrix (approximation)
        focal_length = width
        center = (width / 2, height / 2)
        camera_matrix = np.array([
            [focal_length, 0, center[0]],
            [0, focal_length, center[1]],
            [0, 0, 1]
        ], dtype=np.float64)

        # Assume no lens distortion
        dist_coeffs = np.zeros((4, 1))

        try:
            # Solve PnP
            success, rotation_vector, translation_vector = cv2.solvePnP(
                model_points,
                image_points,
                camera_matrix,
                dist_coeffs,
                flags=cv2.SOLVEPNP_ITERATIVE
            )

            if not success:
                return {"pitch": 0.0, "yaw": 0.0, "roll": 0.0, "error": "PnP solve failed"}

            # Convert rotation vector to rotation matrix
            rotation_matrix, _ = cv2.Rodrigues(rotation_vector)

            # Calculate Euler angles
            pitch = np.arctan2(rotation_matrix[2, 1], rotation_matrix[2, 2])
            yaw = np.arctan2(-rotation_matrix[2, 0], 
                            np.sqrt(rotation_matrix[2, 1]**2 + rotation_matrix[2, 2]**2))
            roll = np.arctan2(rotation_matrix[1, 0], rotation_matrix[0, 0])

            # Convert to degrees
            pitch_deg = np.degrees(pitch)
            yaw_deg = np.degrees(yaw)
            roll_deg = np.degrees(roll)

            return {
                "pitch": round(float(pitch_deg), 2),
                "yaw": round(float(yaw_deg), 2),
                "roll": round(float(roll_deg), 2),
            }
        except Exception as e:
            return {"pitch": 0.0, "yaw": 0.0, "roll": 0.0, "error": str(e)}

    def _calculate_face_visibility(self, landmarks) -> float:
        """
        Calculate face visibility score based on landmark visibility.
        Higher score = more visible face.
        """
        visibility_sum = 0.0
        count = 0
        for lm in landmarks:
            if hasattr(lm, 'visibility'):
                visibility_sum += lm.visibility
                count += 1
        
        if count == 0:
            return 1.0  # Assume visible if no visibility data
        
        return visibility_sum / count

    def _detect_face_down(self, landmarks) -> bool:
        """
        Detect if face is oriented downward (face-down position).
        Uses nose tip and forehead landmarks.
        """
        # Nose tip (1) should be significantly higher than forehead (10) if face down
        nose_tip = landmarks[1]
        forehead = landmarks[10]
        
        # If nose is much lower (higher y value) than forehead, face might be down
        nose_forehead_diff = nose_tip.y - forehead.y
        
        # Also check if many landmarks have low visibility
        visibility_score = self._calculate_face_visibility(landmarks)
        
        # Face down if nose is below forehead OR low visibility
        return nose_forehead_diff > 0.15 or visibility_score < 0.3


_FACE_MESH_ANALYZER: Optional[FaceMeshAnalyzer] = None
_FACE_MESH_LOCK = threading.Lock()


def get_face_mesh_analyzer() -> FaceMeshAnalyzer:
    """Return singleton face mesh analyzer."""
    global _FACE_MESH_ANALYZER
    if _FACE_MESH_ANALYZER is None:
        with _FACE_MESH_LOCK:
            if _FACE_MESH_ANALYZER is None:
                _FACE_MESH_ANALYZER = FaceMeshAnalyzer()
    return _FACE_MESH_ANALYZER
