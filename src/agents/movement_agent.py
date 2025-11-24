"""
Optical-flow movement tracking agent.

Uses dense Farnebäck optical flow to capture micro and macro movements between
frames. Maintains temporal memory to flag sudden jerks or extended stillness.
"""
from __future__ import annotations

import threading
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Dict, Optional

import cv2
import numpy as np

from src.config import get_settings


@dataclass
class MovementState:
    prev_gray: Optional[np.ndarray] = None
    prev_score: float = 0.0
    prev_timestamp: Optional[datetime] = None
    still_duration: float = 0.0
    initialized: bool = False


class OpticalFlowMovementTracker:
    """Stateful optical flow tracker."""

    def __init__(self) -> None:
        settings = get_settings()
        self.state = MovementState()
        self.still_threshold = settings.MOVEMENT_STILL_THRESHOLD
        self.micro_threshold = settings.MOVEMENT_MICRO_THRESHOLD
        self.major_threshold = settings.MOVEMENT_MAJOR_THRESHOLD
        self.jerk_delta = settings.MOVEMENT_JERK_DELTA
        self.stillness_alert_threshold = settings.MOVEMENT_STILLNESS_ALERT_SECONDS

    def analyze(self, frame_bgr: np.ndarray) -> Dict[str, Any]:
        now = datetime.utcnow()
        gray = cv2.cvtColor(frame_bgr, cv2.COLOR_BGR2GRAY)

        if not self.state.initialized or self.state.prev_gray is None:
            self.state.prev_gray = gray
            self.state.prev_timestamp = now
            self.state.initialized = True
            return {
                "movement_score": 0.0,
                "movement_type": "initializing",
                "sudden_jerk": False,
                "stillness_duration_s": 0.0,
                "timestamp": now.isoformat(),
                "notes": "Tracker warming up",
            }

        dt = (
            (now - self.state.prev_timestamp).total_seconds()
            if self.state.prev_timestamp
            else 0.0
        )

        flow = cv2.calcOpticalFlowFarneback(
            self.state.prev_gray,
            gray,
            None,
            0.5,
            3,
            15,
            3,
            5,
            1.2,
            0,
        )
        mag, _ = cv2.cartToPolar(flow[..., 0], flow[..., 1])
        score = float(np.mean(mag))

        movement_type = self._categorize(score)
        sudden_jerk = score - self.state.prev_score > self.jerk_delta

        if movement_type == "still" and dt > 0:
            self.state.still_duration += dt
        else:
            self.state.still_duration = 0.0

        self.state.prev_gray = gray
        self.state.prev_score = score
        self.state.prev_timestamp = now

        return {
            "movement_score": round(score, 4),
            "movement_type": movement_type,
            "sudden_jerk": sudden_jerk,
            "stillness_duration_s": round(self.state.still_duration, 2),
            "stillness_exceeded": self.state.still_duration >= self.stillness_alert_threshold,
            "timestamp": now.isoformat(),
            "notes": self._movement_notes(movement_type, sudden_jerk),
        }

    def _categorize(self, score: float) -> str:
        if score <= self.still_threshold:
            return "still"
        if score <= self.micro_threshold:
            return "micro_movement"
        if score <= self.major_threshold:
            return "active"
        return "major_movement"

    @staticmethod
    def _movement_notes(movement_type: str, sudden_jerk: bool) -> str:
        notes_map = {
            "still": "Barely perceptible motion",
            "micro_movement": "Minor limb movement detected",
            "active": "Normal active motion",
            "major_movement": "Large movement burst",
            "initializing": "Tracker warming up",
        }
        notes = notes_map.get(movement_type, "")
        if sudden_jerk:
            notes = (notes + " " if notes else "") + "Sudden jerk detected"
        return notes.strip()


_MOVEMENT_TRACKER: Optional[OpticalFlowMovementTracker] = None
_MOVEMENT_LOCK = threading.Lock()


def get_movement_tracker() -> OpticalFlowMovementTracker:
    """Return singleton optical flow tracker."""
    global _MOVEMENT_TRACKER
    if _MOVEMENT_TRACKER is None:
        with _MOVEMENT_LOCK:
            if _MOVEMENT_TRACKER is None:
                _MOVEMENT_TRACKER = OpticalFlowMovementTracker()
    return _MOVEMENT_TRACKER

