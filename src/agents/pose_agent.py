"""
Pose estimation agent powered by MediaPipe.

Determines coarse posture classes (sleeping, sitting, standing, rolling,
unusual) and exports normalized keypoints for downstream fusion.
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


class PoseAnalyzer:
    """Thin wrapper around MediaPipe Pose to classify infant posture."""

    def __init__(self) -> None:
        if mp is None:
            self._pose = None
            return

        self._pose = mp.solutions.pose.Pose(
            static_image_mode=True,
            model_complexity=1,
            enable_segmentation=False,
            min_detection_confidence=0.5,
            min_tracking_confidence=0.5,
        )
        self._landmarks_enum = mp.solutions.pose.PoseLandmark

    def close(self) -> None:
        if self._pose is not None:
            self._pose.close()

    def analyze(
        self,
        frame_bgr: np.ndarray,
        focus_box: Optional[Dict[str, float]] = None,
    ) -> Dict[str, Any]:
        if mp is None or self._pose is None:
            return {
                "error": "mediapipe not installed - run `pip install mediapipe`",
                "model_loaded": False,
            }

        roi = frame_bgr
        if focus_box:
            x1, y1, x2, y2 = (
                int(focus_box["bbox"][0]),
                int(focus_box["bbox"][1]),
                int(focus_box["bbox"][2]),
                int(focus_box["bbox"][3]),
            )
            x1 = max(x1 - 20, 0)
            y1 = max(y1 - 20, 0)
            x2 = min(x2 + 20, frame_bgr.shape[1] - 1)
            y2 = min(y2 + 20, frame_bgr.shape[0] - 1)
            roi = frame_bgr[y1:y2, x1:x2]
            if roi.size == 0:
                roi = frame_bgr

        frame_rgb = cv2.cvtColor(roi, cv2.COLOR_BGR2RGB)
        result = self._pose.process(frame_rgb)

        if not result.pose_landmarks:
            return {
                "model_loaded": True,
                "pose_label": "unknown",
                "confidence": 0.0,
                "keypoints": [],
                "reason": "Pose landmarks not detected",
            }

        landmarks = result.pose_landmarks.landmark
        keypoints = [
            {
                "name": self._landmarks_enum(i).name.lower(),
                "x": round(pt.x, 4),
                "y": round(pt.y, 4),
                "z": round(pt.z, 4),
                "visibility": round(pt.visibility, 4),
            }
            for i, pt in enumerate(landmarks)
        ]

        label, confidence, reason = self._classify_posture(landmarks)

        return {
            "model_loaded": True,
            "pose_label": label,
            "confidence": round(confidence, 4),
            "reason": reason,
            "keypoints": keypoints,
        }

    def _classify_posture(self, landmarks) -> tuple[str, float, str]:
        def point(name: str):
            idx = getattr(self._landmarks_enum, name).value
            return landmarks[idx]

        try:
            ls, rs = point("LEFT_SHOULDER"), point("RIGHT_SHOULDER")
            lh, rh = point("LEFT_HIP"), point("RIGHT_HIP")
            la, ra = point("LEFT_ANKLE"), point("RIGHT_ANKLE")
            nose = point("NOSE")
        except Exception:
            return "unknown", 0.0, "Missing key landmarks"

        shoulder_y = (ls.y + rs.y) / 2
        hip_y = (lh.y + rh.y) / 2
        ankle_y = (la.y + ra.y) / 2

        torso_vertical = abs(hip_y - shoulder_y)
        shoulder_diff = abs(ls.y - rs.y)
        hip_diff = abs(lh.y - rh.y)
        nose_height = nose.y

        visibilities = [
            ls.visibility,
            rs.visibility,
            lh.visibility,
            rh.visibility,
            la.visibility,
            ra.visibility,
        ]
        confidence = float(np.clip(np.mean(visibilities), 0.0, 1.0))

        if torso_vertical < 0.06 and shoulder_diff < 0.04:
            return "sleeping", confidence, "Torso almost horizontal"

        if ankle_y < hip_y - 0.05 and torso_vertical > 0.12:
            return "standing", confidence, "Ankles far below hips"

        if hip_y < ankle_y - 0.03 and torso_vertical > 0.08 and nose_height < shoulder_y:
            return "sitting", confidence, "Hips aligned above ankles"

        if shoulder_diff > 0.08 or hip_diff > 0.08:
            return "rolling", confidence, "Left/right side height mismatch"

        return "unusual_posture", confidence, "No template matched"


_POSE_ANALYZER: Optional[PoseAnalyzer] = None
_POSE_LOCK = threading.Lock()


def get_pose_analyzer() -> PoseAnalyzer:
    """Return singleton pose analyzer."""
    global _POSE_ANALYZER
    if _POSE_ANALYZER is None:
        with _POSE_LOCK:
            if _POSE_ANALYZER is None:
                _POSE_ANALYZER = PoseAnalyzer()
    return _POSE_ANALYZER

