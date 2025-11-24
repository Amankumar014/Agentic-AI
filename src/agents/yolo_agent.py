"""
YOLO-based baby/adult detector.

Provides structured detections (bbox, confidence, class) for the LangGraph
workflow. Falls back gracefully when the YOLO runtime is unavailable.
"""
from __future__ import annotations

import threading
from dataclasses import dataclass
from typing import Any, Dict, List, Optional

import cv2
import numpy as np

from src.config import get_settings

try:
    from ultralytics import YOLO  # type: ignore
except Exception:  # pragma: no cover - optional dependency at runtime
    YOLO = None


@dataclass
class DetectionBox:
    """Structured detection metadata."""

    label: str
    confidence: float
    bbox: List[float]
    bbox_normalized: List[float]
    class_id: int
    area_ratio: float


class YOLOBabyDetector:
    """
    Wrapper around Ultralytics YOLO model with baby/adult heuristics.
    """

    def __init__(self, model_path: Optional[str] = None) -> None:
        settings = get_settings()
        self.model_path = model_path or settings.YOLO_MODEL_PATH or "yolov8n.pt"
        self._model = None
        self._lock = threading.Lock()
        self._model_name = None

    def _load_model(self):
        if YOLO is None:
            return None

        if self._model is not None:
            return self._model

        with self._lock:
            if self._model is None:
                try:
                    self._model = YOLO(self.model_path)
                    self._model_name = getattr(self._model, "model", None)
                    print(f"✅ YOLO model loaded from {self.model_path}")
                except Exception as exc:  # pragma: no cover - runtime dependency
                    print(f"❌ Failed to load YOLO model: {exc}")
                    self._model = None
            return self._model

    def detect(self, frame_bgr: np.ndarray) -> Dict[str, Any]:
        """
        Run YOLO detection on the provided frame.
        """
        if YOLO is None:
            return {
                "error": "Ultralytics not installed - run `pip install ultralytics`",
                "model_loaded": False,
            }

        model = self._load_model()
        if model is None:
            return {
                "error": f"Unable to load YOLO model from {self.model_path}",
                "model_loaded": False,
            }

        frame_h, frame_w = frame_bgr.shape[:2]

        try:
            results = model(frame_bgr, verbose=False)
        except Exception as exc:  # pragma: no cover - runtime network/model errors
            return {
                "error": f"YOLO inference failed: {exc}",
                "model_loaded": False,
            }

        detections: List[DetectionBox] = []
        baby_candidates: List[DetectionBox] = []
        adult_candidates: List[DetectionBox] = []
        names_map = results[0].names if results else {}

        for result in results:
            boxes = getattr(result, "boxes", None)
            if boxes is None:
                continue

            for box in boxes:
                xyxy = box.xyxy[0].tolist()
                x1, y1, x2, y2 = map(float, xyxy)
                conf = float(box.conf[0]) if hasattr(box.conf, "__len__") else float(box.conf)
                class_id = int(box.cls[0]) if hasattr(box.cls, "__len__") else int(box.cls)
                label = names_map.get(class_id, str(class_id))

                bbox = [x1, y1, x2, y2]
                bbox_norm = [
                    x1 / frame_w,
                    y1 / frame_h,
                    x2 / frame_w,
                    y2 / frame_h,
                ]
                area_ratio = ((x2 - x1) * (y2 - y1)) / float(frame_w * frame_h)

                detection = DetectionBox(
                    label=label,
                    confidence=conf,
                    bbox=bbox,
                    bbox_normalized=bbox_norm,
                    class_id=class_id,
                    area_ratio=area_ratio,
                )
                detections.append(detection)

                if label.lower() in {"person", "baby", "child"}:
                    if label.lower() == "baby" or area_ratio < 0.22:
                        baby_candidates.append(detection)
                    else:
                        adult_candidates.append(detection)

        total_people = len(baby_candidates) + len(adult_candidates)
        baby_detected = len(baby_candidates) > 0
        adult_detected = len(adult_candidates) > 0
        adult_intrusion = baby_detected and adult_detected

        primary_baby = None
        if baby_candidates:
            # Prefer the smallest bounding box (likely the baby)
            primary_baby = min(baby_candidates, key=lambda d: d.area_ratio)

        structured_detections = [
            {
                "label": det.label,
                "confidence": round(det.confidence, 4),
                "bbox": [round(v, 2) for v in det.bbox],
                "bbox_normalized": [round(v, 4) for v in det.bbox_normalized],
                "class_id": det.class_id,
                "area_ratio": round(det.area_ratio, 6),
            }
            for det in detections
        ]

        result_payload: Dict[str, Any] = {
            "model_loaded": True,
            "model_name": str(self._model_name) if self._model_name else "ultralytics",
            "frame_size": {"width": frame_w, "height": frame_h},
            "detections": structured_detections,
            "baby_detected": baby_detected,
            "adult_detected": adult_detected,
            "adult_intrusion": adult_intrusion,
            "multiple_persons": total_people >= 2,
            "person_count": total_people,
        }

        if primary_baby:
            result_payload["primary_baby_box"] = {
                "label": primary_baby.label,
                "confidence": round(primary_baby.confidence, 4),
                "bbox": [round(v, 2) for v in primary_baby.bbox],
                "bbox_normalized": [round(v, 4) for v in primary_baby.bbox_normalized],
            }

        return result_payload


_YOLO_INSTANCE: Optional[YOLOBabyDetector] = None
_YOLO_LOCK = threading.Lock()


def get_yolo_detector() -> YOLOBabyDetector:
    """Return singleton YOLO detector instance."""
    global _YOLO_INSTANCE
    if _YOLO_INSTANCE is None:
        with _YOLO_LOCK:
            if _YOLO_INSTANCE is None:
                _YOLO_INSTANCE = YOLOBabyDetector()
    return _YOLO_INSTANCE

