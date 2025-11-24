"""
Emotion detection agent using a pretrained Keras model.

Loads ml_models/best_model.h5 (if available) to classify facial expressions
into the categories required by the monitoring workflow. Falls back to simple
heuristics when the model or dependencies are missing.
"""
from __future__ import annotations

import threading
from pathlib import Path
from typing import Any, Dict, Optional

import cv2
import numpy as np

from src.config import get_settings

try:
    import tensorflow as tf  # type: ignore
except Exception:  # pragma: no cover - optional dependency
    tf = None


TARGET_LABELS = ["happy", "neutral", "crying", "uncomfortable", "pain", "distress"]


class EmotionDetector:
    """TensorFlow-based emotion classifier with graceful degradation."""

    def __init__(self, model_path: Optional[str] = None) -> None:
        settings = get_settings()
        project_root = Path(__file__).parent.parent
        resolved = model_path or settings.EMOTION_MODEL_PATH
        path = Path(resolved)
        if not path.is_absolute():
            path = (project_root / resolved).resolve()

        self.model_path = path
        self._model = None
        self._lock = threading.Lock()
        self._input_size = (64, 64)
        self._channel_last = True
        self._face_detector = cv2.CascadeClassifier(
            cv2.data.haarcascades + "haarcascade_frontalface_default.xml"
        )

    def _load_model(self):
        if tf is None:
            return None

        if self._model is not None:
            return self._model

        if not self.model_path.exists():
            print(f"⚠️  Emotion model not found at {self.model_path}")
            return None

        with self._lock:
            if self._model is None:
                try:
                    self._model = tf.keras.models.load_model(self.model_path)
                    input_shape = getattr(self._model, "input_shape", None)
                    if input_shape and len(input_shape) >= 3:
                        self._input_size = (input_shape[1], input_shape[2])
                        self._channel_last = len(input_shape) == 4
                    print(f"✅ Emotion model loaded from {self.model_path}")
                except Exception as exc:  # pragma: no cover
                    print(f"❌ Failed to load emotion model: {exc}")
                    self._model = None
        return self._model

    def infer(
        self,
        frame_bgr: np.ndarray,
        baby_box: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        roi = self._extract_roi(frame_bgr, baby_box)
        if roi.size == 0:
            return {
                "emotion_label": "neutral",
                "probability": 0.0,
                "source": "no_face",
                "distribution": {},
                "notes": "No face detected",
            }

        model = self._load_model()
        if model is None:
            label, score, notes = self._heuristic_label(roi)
            return {
                "emotion_label": label,
                "probability": score,
                "source": "heuristic",
                "distribution": {},
                "notes": notes,
            }

        roi_gray = cv2.cvtColor(roi, cv2.COLOR_BGR2GRAY)
        resized = cv2.resize(roi_gray, self._input_size, interpolation=cv2.INTER_AREA)
        normalized = resized.astype("float32") / 255.0
        if self._channel_last:
            normalized = normalized.reshape(1, self._input_size[0], self._input_size[1], 1)
        else:
            normalized = normalized.reshape(1, 1, self._input_size[0], self._input_size[1])

        try:
            preds = model.predict(normalized, verbose=0)[0]
        except Exception as exc:  # pragma: no cover - runtime inference errors
            print(f"⚠️  Emotion inference failed: {exc}")
            label, score, notes = self._heuristic_label(roi)
            return {
                "emotion_label": label,
                "probability": score,
                "source": "heuristic_fallback",
                "distribution": {},
                "notes": notes,
            }

        mapped = self._map_distribution(preds)
        label = max(mapped, key=mapped.get)
        return {
            "emotion_label": label,
            "probability": round(mapped[label], 4),
            "distribution": {k: round(v, 4) for k, v in mapped.items()},
            "source": "model",
            "notes": "TensorFlow emotion model prediction",
        }

    def _extract_roi(
        self,
        frame_bgr: np.ndarray,
        baby_box: Optional[Dict[str, Any]],
    ) -> np.ndarray:
        if baby_box and "bbox" in baby_box:
            x1, y1, x2, y2 = map(int, baby_box["bbox"])
            pad = 10
            x1 = max(x1 - pad, 0)
            y1 = max(y1 - pad, 0)
            x2 = min(x2 + pad, frame_bgr.shape[1])
            y2 = min(y2 + pad, frame_bgr.shape[0])
            return frame_bgr[y1:y2, x1:x2]

        gray = cv2.cvtColor(frame_bgr, cv2.COLOR_BGR2GRAY)
        faces = self._face_detector.detectMultiScale(gray, scaleFactor=1.2, minNeighbors=4)
        if len(faces) == 0:
            return frame_bgr
        x, y, w, h = faces[0]
        return frame_bgr[y : y + h, x : x + w]

    @staticmethod
    def _heuristic_label(roi: np.ndarray) -> tuple[str, float, str]:
        gray = cv2.cvtColor(roi, cv2.COLOR_BGR2GRAY)
        lap = cv2.Laplacian(gray, cv2.CV_64F).var()
        std = np.std(gray)
        mean = np.mean(gray)

        # Very low variance = sleeping/calm
        if std < 15:
            return "neutral", 0.55, "Low variance / possibly sleeping or calm"
        
        # Extremely high variance + high Laplacian = potential crying
        # Raised thresholds to reduce false positives
        if lap > 250 and std > 45:
            return "crying", 0.55, "Very high texture variance (possible crying)"
        
        # High std but not extreme = could be active/awake, not necessarily distress
        if std > 50:
            return "uncomfortable", 0.5, "High intensity variance (active or uncomfortable)"
        
        # Moderate variance = likely awake and neutral/happy
        if std > 20:
            return "neutral", 0.6, "Moderate variance (awake and moving)"
        
        # Default to neutral (not uncomfortable)
        return "neutral", 0.55, "Default heuristic: neutral state"

    def _map_distribution(self, preds: np.ndarray) -> Dict[str, float]:
        preds = preds.astype(float)
        preds = preds / preds.sum() if preds.sum() else preds

        mapped = {label: 0.0 for label in TARGET_LABELS}

        model_labels = self._infer_model_labels(len(preds))
        for score, model_label in zip(preds, model_labels):
            key = self._map_label(model_label)
            mapped[key] += float(score)

        return mapped

    @staticmethod
    def _infer_model_labels(length: int) -> list[str]:
        # Common FER order fallback
        default = ["angry", "disgust", "fear", "happy", "sad", "surprise", "neutral"]
        if length == len(default):
            return default
        # If already matches TARGET_LABELS
        if length == len(TARGET_LABELS):
            return TARGET_LABELS
        # Otherwise create generic labels
        return [f"class_{i}" for i in range(length)]

    @staticmethod
    def _map_label(label: str) -> str:
        label = label.lower()
        mapping = {
            "happy": "happy",
            "neutral": "neutral",
            "sad": "crying",
            "fear": "distress",
            "angry": "distress",
            "disgust": "uncomfortable",
            "surprise": "uncomfortable",
            "pain": "pain",
            "crying": "crying",
            "distress": "distress",
        }
        return mapping.get(label, "uncomfortable")


_EMOTION_DETECTOR: Optional[EmotionDetector] = None
_EMOTION_LOCK = threading.Lock()


def get_emotion_detector() -> EmotionDetector:
    """Return singleton emotion detector."""
    global _EMOTION_DETECTOR
    if _EMOTION_DETECTOR is None:
        with _EMOTION_LOCK:
            if _EMOTION_DETECTOR is None:
                _EMOTION_DETECTOR = EmotionDetector()
    return _EMOTION_DETECTOR

