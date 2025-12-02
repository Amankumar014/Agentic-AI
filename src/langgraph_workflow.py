"""
LangGraph workflow orchestrating multi-agent CV + LLM baby monitoring.
Combines classic computer vision detectors and Azure Vision reasoning
into a robust analysis and alerting pipeline.
"""
import asyncio
import json
from datetime import datetime
from typing import Any, Dict, List, Optional, TypedDict

import cv2
import numpy as np
from langgraph.graph import StateGraph

from src.agents import (
    get_emotion_detector,
    get_face_mesh_analyzer,
    get_iris_tracker,
    get_movement_tracker,
    get_pose_analyzer,
    get_yolo_detector,
)
from src.config import get_settings
from src.agent import evaluate_fused_state
from src.audio_agent_placeholder import extract_librosa_features, classify_cry
from src.azure_vision import analyze_multimodal_state
from src.models import AlertLog, FrameAnalysisLog, get_session
from src.utils import save_bytes_to_temp


AGENT_METADATA: Dict[str, Dict[str, Any]] = {
    "camera_input": {
        "name": "Camera Input Agent",
        "purpose": "Decode incoming bytes, persist frames/audio, and hydrate state.",
        "inputs": ["frame_bytes", "audio_bytes"],
        "outputs": ["frame_path", "audio_path", "audio_result"],
        "model": "Direct Python I/O",
    },
    "yolo_agent": {
        "name": "YOLO Baby Detector",
        "purpose": "Pretrained YOLO model detecting babies, adults, intrusions, and multi-person presence.",
        "inputs": ["frame_bgr"],
        "outputs": ["yolo_result"],
        "model": "Ultralytics YOLO",
    },
    "pose_agent": {
        "name": "Pose Estimation Agent",
        "purpose": "MediaPipe pose estimation to classify sleeping/sitting/standing/rolling/unusual postures.",
        "inputs": ["frame_bgr", "yolo_result"],
        "outputs": ["pose_result"],
        "model": "MediaPipe Pose",
    },
    "movement_agent": {
        "name": "Movement Tracking Agent",
        "purpose": "Optical-flow tracker capturing micro-movements, jerks, and stillness duration.",
        "inputs": ["frame_bgr"],
        "outputs": ["movement_result"],
        "model": "Farnebäck Optical Flow",
    },
    "emotion_agent": {
        "name": "Emotion Detection Agent",
        "purpose": "TensorFlow model (ml_models/best_model.h5) classifying baby facial emotion.",
        "inputs": ["frame_bgr", "yolo_result"],
        "outputs": ["emotion_result"],
        "model": "TensorFlow / Haar cascade ROI",
    },
    "face_mesh_agent": {
        "name": "Face Mesh Analysis Agent",
        "purpose": "MediaPipe Face Mesh extracting 468 landmarks, eye/mouth ratios, head orientation, breathing, and face-down detection.",
        "inputs": ["frame_bgr", "yolo_result"],
        "outputs": ["face_mesh_result"],
        "model": "MediaPipe Face Mesh",
    },
    "iris_tracking_agent": {
        "name": "Iris Tracking Agent",
        "purpose": "MediaPipe Iris for precise eye tracking, gaze direction, blinking frequency, and sleep detection.",
        "inputs": ["frame_bgr", "yolo_result"],
        "outputs": ["iris_tracking_result"],
        "model": "MediaPipe Iris",
    },
    "fusion_agent": {
        "name": "Azure Vision Fusion Agent",
        "purpose": "Azure GPT-4o Vision reasoning over fused structured signals plus the raw frame.",
        "inputs": ["frame_bytes", "yolo_result", "pose_result", "movement_result", "emotion_result", "face_mesh_result", "iris_tracking_result"],
        "outputs": ["fusion_result"],
        "model": "Azure OpenAI GPT-4o",
    },
    "alert_agent": {
        "name": "State Evaluation & Alert Agent",
        "purpose": "Fuse final Azure classification with signals, enforce cooldowns, and trigger notifications.",
        "inputs": ["fusion_result", "fused_context"],
        "outputs": ["decision_result", "alert_result"],
        "model": "Rule-based + Email/SMS Notifier",
    },
    "logger_agent": {
        "name": "Database Logger Agent",
        "purpose": "Persist multi-modal results and alert history to SQLite via SQLModel.",
        "inputs": ["fusion_result", "decision_result", "alert_result"],
        "outputs": ["log_ids"],
        "model": "SQLModel",
    },
}


class WorkflowState(TypedDict, total=False):
    frame_bytes: Optional[bytes]
    audio_bytes: Optional[bytes]
    frame_path: Optional[str]
    audio_path: Optional[str]
    frame_bgr: Optional[Any]
    audio_result: Optional[Dict[str, Any]]
    yolo_result: Optional[Dict[str, Any]]
    pose_result: Optional[Dict[str, Any]]
    movement_result: Optional[Dict[str, Any]]
    emotion_result: Optional[Dict[str, Any]]
    face_mesh_result: Optional[Dict[str, Any]]
    iris_tracking_result: Optional[Dict[str, Any]]
    fused_context: Dict[str, Any]
    fusion_result: Optional[Dict[str, Any]]
    decision_result: Optional[Dict[str, Any]]
    alert_result: Optional[Dict[str, Any]]
    log_ids: Dict[str, Optional[int]]
    timestamp: str
    status: str
    errors: List[str]


def log_agent_input(agent: str, state: WorkflowState) -> None:
    metadata = AGENT_METADATA.get(agent, {})
    inputs = metadata.get("inputs", [])
    print(f"\n{'=' * 70}")
    print(f"🔵 INPUT → {metadata.get('name', agent)}")
    print(f"{'=' * 70}")
    for key in inputs:
        value = state.get(key)
        if isinstance(value, bytes):
            print(f"  • {key}: <bytes len={len(value)}>")
        elif isinstance(value, np.ndarray):
            print(f"  • {key}: ndarray shape={value.shape}")
        elif isinstance(value, dict):
            preview = json.dumps(value)[:200]
            print(f"  • {key}: {preview}")
        else:
            print(f"  • {key}: {value}")


def log_agent_output(agent: str, state: WorkflowState, success: bool = True) -> None:
    metadata = AGENT_METADATA.get(agent, {})
    outputs = metadata.get("outputs", [])
    print(f"\n{'✅' if success else '❌'} OUTPUT ← {metadata.get('name', agent)}")
    print(f"{'=' * 70}")
    for key in outputs:
        value = state.get(key)
        if isinstance(value, dict):
            preview = json.dumps(value)[:200]
            print(f"  • {key}: {preview}")
        elif isinstance(value, np.ndarray):
            print(f"  • {key}: ndarray shape={value.shape}")
        else:
            print(f"  • {key}: {value}")
    if state.get("errors"):
        print("Errors:")
        for err in state["errors"]:
            print(f"  - {err}")


def _decode_frame(frame_bytes: Optional[bytes]) -> Optional[np.ndarray]:
    if not frame_bytes:
        return None
    np_buffer = np.frombuffer(frame_bytes, dtype=np.uint8)
    frame = cv2.imdecode(np_buffer, cv2.IMREAD_COLOR)
    return frame


def _analyze_audio(audio_path: str) -> Dict[str, Any]:
    features = extract_librosa_features(audio_path)
    classification = classify_cry(features)
    return {
        "features": features,
        "is_crying": classification.get("is_crying", False),
        "confidence": classification.get("confidence", 0.0),
        "model_loaded": classification.get("model_loaded", False),
    }


def _build_fused_context(state: WorkflowState) -> Dict[str, Any]:
    return {
        "yolo_result": state.get("yolo_result"),
        "pose_result": state.get("pose_result"),
        "movement_result": state.get("movement_result"),
        "emotion_result": state.get("emotion_result"),
        "face_mesh_result": state.get("face_mesh_result"),
        "iris_tracking_result": state.get("iris_tracking_result"),
        "audio_result": state.get("audio_result"),
    }


def camera_input_node(state: WorkflowState) -> WorkflowState:
    agent = "camera_input"
    log_agent_input(agent, state)
    try:
        if state.get("frame_bytes"):
            state["frame_path"] = save_bytes_to_temp(state["frame_bytes"], suffix=".jpg")
            state["frame_bgr"] = _decode_frame(state["frame_bytes"])
            if state["frame_bgr"] is None:
                raise ValueError("Failed to decode frame bytes into image")
            print(f"  ✅ Frame saved to {state['frame_path']}")
        else:
            raise ValueError("frame_bytes missing")

        if state.get("audio_bytes"):
            state["audio_path"] = save_bytes_to_temp(state["audio_bytes"], suffix=".wav")
            try:
                state["audio_result"] = _analyze_audio(state["audio_path"])
            except Exception as exc:  # noqa: BLE001
                err = f"audio_analysis: {exc}"
                print(f"  ⚠️  {err}")
                state.setdefault("errors", []).append(err)
        else:
            state["audio_result"] = None

        state["status"] = "input_ready"
        log_agent_output(agent, state)
    except Exception as exc:  # noqa: BLE001
        err = f"camera_input: {exc}"
        state.setdefault("errors", []).append(err)
        state["status"] = "error"
        log_agent_output(agent, state, success=False)
    return state


def yolo_agent_node(state: WorkflowState) -> WorkflowState:
    agent = "yolo_agent"
    log_agent_input(agent, state)
    try:
        frame = state.get("frame_bgr")
        if frame is None:
            raise ValueError("No decoded frame available for YOLO")
        detector = get_yolo_detector()
        result = detector.detect(frame)
        state["yolo_result"] = result
        log_agent_output(agent, state)
    except Exception as exc:  # noqa: BLE001
        err = f"yolo_agent: {exc}"
        state.setdefault("errors", []).append(err)
        state["yolo_result"] = {"error": str(exc), "model_loaded": False}
        log_agent_output(agent, state, success=False)
    return state


def pose_agent_node(state: WorkflowState) -> WorkflowState:
    agent = "pose_agent"
    log_agent_input(agent, state)
    try:
        frame = state.get("frame_bgr")
        if frame is None:
            raise ValueError("No decoded frame available for pose analysis")
        focus = None
        yolo = state.get("yolo_result") or {}
        if isinstance(yolo, dict):
            focus = yolo.get("primary_baby_box")
        pose_model = get_pose_analyzer()
        result = pose_model.analyze(frame, focus_box=focus)
        state["pose_result"] = result
        log_agent_output(agent, state, success=result.get("model_loaded", True))
    except Exception as exc:  # noqa: BLE001
        err = f"pose_agent: {exc}"
        state.setdefault("errors", []).append(err)
        state["pose_result"] = {"error": str(exc), "pose_label": "unknown"}
        log_agent_output(agent, state, success=False)
    return state


def movement_agent_node(state: WorkflowState) -> WorkflowState:
    agent = "movement_agent"
    log_agent_input(agent, state)
    try:
        frame = state.get("frame_bgr")
        if frame is None:
            raise ValueError("No decoded frame available for movement tracking")
        tracker = get_movement_tracker()
        result = tracker.analyze(frame)
        state["movement_result"] = result
        log_agent_output(agent, state)
    except Exception as exc:  # noqa: BLE001
        err = f"movement_agent: {exc}"
        state.setdefault("errors", []).append(err)
        state["movement_result"] = {"error": str(exc)}
        log_agent_output(agent, state, success=False)
    return state


def emotion_agent_node(state: WorkflowState) -> WorkflowState:
    agent = "emotion_agent"
    log_agent_input(agent, state)
    try:
        frame = state.get("frame_bgr")
        if frame is None:
            raise ValueError("No decoded frame available for emotion detection")
        focus = None
        yolo = state.get("yolo_result") or {}
        if isinstance(yolo, dict):
            focus = yolo.get("primary_baby_box")
        detector = get_emotion_detector()
        result = detector.infer(frame, baby_box=focus)
        state["emotion_result"] = result
        log_agent_output(agent, state, success=result.get("source") != "no_face")
    except Exception as exc:  # noqa: BLE001
        err = f"emotion_agent: {exc}"
        state.setdefault("errors", []).append(err)
        state["emotion_result"] = {"error": str(exc), "emotion_label": "neutral"}
        log_agent_output(agent, state, success=False)
    return state


def face_mesh_agent_node(state: WorkflowState) -> WorkflowState:
    agent = "face_mesh_agent"
    log_agent_input(agent, state)
    
    # Check if Face Mesh is enabled
    settings = get_settings()
    if not settings.ENABLE_FACE_MESH:
        state["face_mesh_result"] = {
            "enabled": False,
            "reason": "Face Mesh disabled in settings"
        }
        print("  ⚠️  Face Mesh detection disabled in configuration")
        log_agent_output(agent, state)
        return state
    
    try:
        frame = state.get("frame_bgr")
        if frame is None:
            raise ValueError("No decoded frame available for face mesh analysis")
        
        # Only run if baby detected by YOLO
        yolo = state.get("yolo_result") or {}
        baby_detected = yolo.get("baby_detected", False) if isinstance(yolo, dict) else False
        
        if not baby_detected:
            state["face_mesh_result"] = {
                "skipped": True,
                "reason": "No baby detected by YOLO - skipping face mesh analysis"
            }
            print("  ⏭️  Skipping face mesh: no baby detected")
            log_agent_output(agent, state)
            return state
        
        focus = yolo.get("primary_baby_box") if isinstance(yolo, dict) else None
        analyzer = get_face_mesh_analyzer()
        result = analyzer.analyze(frame, focus_box=focus)
        state["face_mesh_result"] = result
        
        # Log key findings
        if result.get("face_detected"):
            print(f"  ✅ Face mesh detected: {result.get('landmarks_count')} landmarks")
            print(f"     Eyes: {result.get('eyes_state')}, Mouth: {result.get('mouth_state')}")
            if result.get("face_down_detected"):
                print(f"     ⚠️  Face-down position detected!")
        
        log_agent_output(agent, state, success=result.get("model_loaded", True))
    except Exception as exc:  # noqa: BLE001
        err = f"face_mesh_agent: {exc}"
        state.setdefault("errors", []).append(err)
        state["face_mesh_result"] = {"error": str(exc), "face_detected": False}
        log_agent_output(agent, state, success=False)
    return state


def iris_tracking_agent_node(state: WorkflowState) -> WorkflowState:
    agent = "iris_tracking_agent"
    log_agent_input(agent, state)
    
    # Check if Iris Tracking is enabled
    settings = get_settings()
    if not settings.ENABLE_IRIS_TRACKING:
        state["iris_tracking_result"] = {
            "enabled": False,
            "reason": "Iris tracking disabled in settings"
        }
        print("  ⚠️  Iris tracking disabled in configuration")
        log_agent_output(agent, state)
        return state
    
    try:
        frame = state.get("frame_bgr")
        if frame is None:
            raise ValueError("No decoded frame available for iris tracking")
        
        # Only run if baby detected by YOLO
        yolo = state.get("yolo_result") or {}
        baby_detected = yolo.get("baby_detected", False) if isinstance(yolo, dict) else False
        
        if not baby_detected:
            state["iris_tracking_result"] = {
                "skipped": True,
                "reason": "No baby detected by YOLO - skipping iris tracking"
            }
            print("  ⏭️  Skipping iris tracking: no baby detected")
            log_agent_output(agent, state)
            return state
        
        focus = yolo.get("primary_baby_box") if isinstance(yolo, dict) else None
        tracker = get_iris_tracker()
        result = tracker.analyze(frame, focus_box=focus)
        state["iris_tracking_result"] = result
        
        # Log key findings
        if result.get("iris_detected"):
            eyes = result.get("eyes_state", "unknown")
            closure_pattern = result.get("closure_pattern", "unknown")
            blink_freq = result.get("blinking", {}).get("frequency_per_minute", 0)
            print(f"  ✅ Iris tracking: Eyes {eyes}, Pattern: {closure_pattern}")
            print(f"     Blink frequency: {blink_freq:.1f}/min")
            if closure_pattern == "sleeping":
                print(f"     😴 Sleep pattern detected")
        
        log_agent_output(agent, state, success=result.get("model_loaded", True))
    except Exception as exc:  # noqa: BLE001
        err = f"iris_tracking_agent: {exc}"
        state.setdefault("errors", []).append(err)
        state["iris_tracking_result"] = {"error": str(exc), "iris_detected": False}
        log_agent_output(agent, state, success=False)
    finally:
        # Release frame to reduce memory pressure; remaining steps use frame_bytes.
        state["frame_bgr"] = None
    return state


def fusion_agent_node(state: WorkflowState) -> WorkflowState:
    agent = "fusion_agent"
    log_agent_input(agent, state)
    try:
        if not state.get("frame_bytes"):
            raise ValueError("frame_bytes missing for multimodal reasoning")
        fused_context = _build_fused_context(state)
        state["fused_context"] = fused_context
        result = asyncio.run(analyze_multimodal_state(state["frame_bytes"], fused_context))
        state["fusion_result"] = result
        state["status"] = "fusion_complete"
        log_agent_output(agent, state, success="error" not in result)
    except Exception as exc:  # noqa: BLE001
        err = f"fusion_agent: {exc}"
        state.setdefault("errors", []).append(err)
        state["fusion_result"] = {"error": str(exc), "final_state": "unknown"}
        log_agent_output(agent, state, success=False)
    return state


def alert_agent_node(state: WorkflowState) -> WorkflowState:
    agent = "alert_agent"
    log_agent_input(agent, state)
    try:
        fusion_result = state.get("fusion_result")
        fused_context = state.get("fused_context", {})
        decision = evaluate_fused_state(fusion_result, fused_context)
        state["decision_result"] = decision
        state["alert_result"] = decision.get("alert_payload")
        state["status"] = "alert_evaluated"
        log_agent_output(agent, state)
    except Exception as exc:  # noqa: BLE001
        err = f"alert_agent: {exc}"
        state.setdefault("errors", []).append(err)
        state["decision_result"] = {"alert": False, "reason": str(exc)}
        state["alert_result"] = {"sent": False, "error": str(exc)}
        log_agent_output(agent, state, success=False)
    return state


def logger_agent_node(state: WorkflowState) -> WorkflowState:
    agent = "logger_agent"
    log_agent_input(agent, state)
    log_ids: Dict[str, Optional[int]] = {}
    try:
        fusion = state.get("fusion_result") or {}
        pose = state.get("pose_result") or {}
        movement = state.get("movement_result") or {}
        payload = {
            "fusion": fusion,
            "pose": pose,
            "movement": movement,
            "emotion": state.get("emotion_result"),
            "yolo": state.get("yolo_result"),
            "face_mesh": state.get("face_mesh_result"),
            "iris_tracking": state.get("iris_tracking_result"),
        }
        if state.get("frame_path"):
            with get_session() as session:
                frame_log = FrameAnalysisLog(
                    frame_path=state["frame_path"],
                    baby_detected=fusion.get("baby_detected", False),
                    movement_level=fusion.get("movement_level") or movement.get("movement_type"),
                    position=pose.get("pose_label"),
                    risk=fusion.get("risk"),
                    raw_response=json.dumps(payload),
                )
                session.add(frame_log)
                session.commit()
                session.refresh(frame_log)
                log_ids["frame_log_id"] = frame_log.id
                print(f"  💾 Frame log stored ({frame_log.id})")
        decision = state.get("decision_result") or {}
        if decision.get("alert"):
            with get_session() as session:
                alert_log = AlertLog(
                    alert_type=decision.get("alert_type") or "fused_state",
                    message=decision.get("reason", "Alert triggered"),
                    delivered=decision.get("notified", False),
                )
                session.add(alert_log)
                session.commit()
                session.refresh(alert_log)
                log_ids["alert_log_id"] = alert_log.id
                print(f"  💾 Alert log stored ({alert_log.id})")
        state["log_ids"] = log_ids
        state["status"] = "complete"
        log_agent_output(agent, state)
    except Exception as exc:  # noqa: BLE001
        err = f"logger_agent: {exc}"
        state.setdefault("errors", []).append(err)
        state["log_ids"] = log_ids
        log_agent_output(agent, state, success=False)
    return state


def create_baby_monitor_workflow():
    graph = StateGraph(WorkflowState)
    graph.add_node("camera_input", camera_input_node)
    graph.add_node("yolo_agent", yolo_agent_node)
    graph.add_node("pose_agent", pose_agent_node)
    graph.add_node("movement_agent", movement_agent_node)
    graph.add_node("emotion_agent", emotion_agent_node)
    graph.add_node("face_mesh_agent", face_mesh_agent_node)
    graph.add_node("iris_tracking_agent", iris_tracking_agent_node)
    graph.add_node("fusion_agent", fusion_agent_node)
    graph.add_node("alert_agent", alert_agent_node)
    graph.add_node("logger_agent", logger_agent_node)

    # Pipeline: camera → YOLO → pose → movement → emotion → face_mesh → iris → fusion → alert → logger
    graph.add_edge("camera_input", "yolo_agent")
    graph.add_edge("yolo_agent", "pose_agent")
    graph.add_edge("pose_agent", "movement_agent")
    graph.add_edge("movement_agent", "emotion_agent")
    graph.add_edge("emotion_agent", "face_mesh_agent")
    graph.add_edge("face_mesh_agent", "iris_tracking_agent")
    graph.add_edge("iris_tracking_agent", "fusion_agent")
    graph.add_edge("fusion_agent", "alert_agent")
    graph.add_edge("alert_agent", "logger_agent")

    graph.set_entry_point("camera_input")
    graph.set_finish_point("logger_agent")
    return graph.compile()


def run(frame_bytes: Optional[bytes] = None, audio_bytes: Optional[bytes] = None) -> Dict[str, Any]:
    print("\n" + "=" * 70)
    print("🍼 BABY MONITOR LANGGRAPH WORKFLOW")
    print("=" * 70)

    initial_state: WorkflowState = {
        "frame_bytes": frame_bytes,
        "audio_bytes": audio_bytes,
        "frame_path": None,
        "audio_path": None,
        "audio_result": None,
        "yolo_result": None,
        "pose_result": None,
        "movement_result": None,
        "emotion_result": None,
        "face_mesh_result": None,
        "iris_tracking_result": None,
        "fusion_result": None,
        "decision_result": None,
        "alert_result": None,
        "log_ids": {},
        "timestamp": datetime.utcnow().isoformat(),
        "status": "initializing",
        "errors": [],
    }

    workflow = create_baby_monitor_workflow()
    try:
        final_state = workflow.invoke(initial_state)
        final_state.pop("frame_bgr", None)
        final_state.pop("frame_bytes", None)
        final_state.pop("audio_bytes", None)
        print("\n✅ WORKFLOW COMPLETE\n")
        if final_state.get("fusion_result"):
            summary = final_state["fusion_result"]
            print(
                f"State: {summary.get('final_state')} | "
                f"Risk: {summary.get('risk')} | "
                f"Confidence: {summary.get('confidence')}"
            )
        decision = final_state.get("decision_result") or {}
        if decision:
            alert = decision.get("alert")
            print(f"Alert Needed: {alert} ({decision.get('reason')})")
        return final_state
    except Exception as exc:  # noqa: BLE001
        error_state = {
            "status": "error",
            "timestamp": datetime.utcnow().isoformat(),
            "errors": [str(exc)],
        }
        print(f"\n❌ WORKFLOW ERROR: {exc}\n")
        return error_state


if __name__ == "__main__":
    from pathlib import Path

    test_image = Path("temp/test_frame.jpg")
    if test_image.exists():
        frame_data = test_image.read_bytes()
    else:
        import io
        from PIL import Image

        img = Image.new("RGB", (320, 240), color="blue")
        buf = io.BytesIO()
        img.save(buf, format="JPEG")
        frame_data = buf.getvalue()

    result = run(frame_bytes=frame_data)
    print("\n📊 Result:")
    print(json.dumps(result, indent=2, default=str))

