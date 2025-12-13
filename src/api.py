"""
FastAPI router for baby monitor API endpoints.
Provides endpoints for frame upload, analysis, alerts, and logs.
"""
import json
from datetime import datetime
from typing import List, Optional

from fastapi import APIRouter, UploadFile, File, Query, HTTPException, WebSocket, WebSocketDisconnect
from starlette.requests import Request
from fastapi.responses import JSONResponse, StreamingResponse
from sqlmodel import select
import asyncio
import numpy as np

from src.config import get_settings
from src.models import get_session, FrameAnalysisLog, AlertLog
from src.langgraph_workflow import run as run_workflow
from src.utils import run_blocking


# Create API router
router = APIRouter()


def _build_combined_facial_state(emotion_result, face_mesh_result, iris_tracking_result):
    """
    Build a combined facial state summary from emotion, face mesh, and iris tracking results.
    
    Returns a structured summary useful for downstream analysis and alerting.
    """
    if not emotion_result and not face_mesh_result and not iris_tracking_result:
        return None
    
    combined = {
        "facial_analysis_available": bool(emotion_result or face_mesh_result or iris_tracking_result),
    }
    
    # Emotion state
    if emotion_result and isinstance(emotion_result, dict):
        combined["emotion"] = {
            "label": emotion_result.get("emotion_label", "unknown"),
            "probability": emotion_result.get("probability", 0.0),
            "source": emotion_result.get("source", "unknown"),
        }
    
    # Face mesh state
    if face_mesh_result and isinstance(face_mesh_result, dict):
        combined["face_mesh"] = {
            "detected": face_mesh_result.get("face_detected", False),
            "eyes_state": face_mesh_result.get("eyes_state", "unknown"),
            "mouth_state": face_mesh_result.get("mouth_state", "unknown"),
            "face_down_detected": face_mesh_result.get("face_down_detected", False),
            "eye_aspect_ratio": face_mesh_result.get("eye_aspect_ratio", {}).get("average", 0.0),
            "mouth_aspect_ratio": face_mesh_result.get("mouth_aspect_ratio", 0.0),
        }
    
    # Iris tracking state
    if iris_tracking_result and isinstance(iris_tracking_result, dict):
        combined["iris_tracking"] = {
            "detected": iris_tracking_result.get("iris_detected", False),
            "eyes_state": iris_tracking_result.get("eyes_state", "unknown"),
            "closure_pattern": iris_tracking_result.get("closure_pattern", "unknown"),
            "blink_frequency": iris_tracking_result.get("blinking", {}).get("frequency_per_minute", 0.0),
            "gaze_direction": iris_tracking_result.get("gaze_direction", {}),
        }
    
    # Aggregate sleep/wake state
    eyes_closed_indicators = []
    
    # Check face mesh
    if face_mesh_result and isinstance(face_mesh_result, dict):
        if face_mesh_result.get("eyes_state") == "closed":
            eyes_closed_indicators.append("face_mesh")
    
    # Check iris tracking
    if iris_tracking_result and isinstance(iris_tracking_result, dict):
        if iris_tracking_result.get("eyes_state") == "closed":
            eyes_closed_indicators.append("iris_tracking")
        if iris_tracking_result.get("closure_pattern") in ["sleeping", "drowsy"]:
            eyes_closed_indicators.append("closure_pattern")
    
    # Determine likely sleep/wake state
    if len(eyes_closed_indicators) >= 2:
        combined["likely_state"] = "sleeping"
    elif len(eyes_closed_indicators) == 1:
        combined["likely_state"] = "drowsy"
    else:
        combined["likely_state"] = "awake"
    
    # Detect crying
    crying_indicators = []
    if emotion_result and isinstance(emotion_result, dict):
        if emotion_result.get("emotion_label") in ["crying", "distress", "pain"]:
            crying_indicators.append("emotion")
    
    if face_mesh_result and isinstance(face_mesh_result, dict):
        if face_mesh_result.get("mouth_state") == "open":
            # Check mouth aspect ratio threshold
            mar = face_mesh_result.get("mouth_aspect_ratio", 0.0)
            if mar > 0.6:  # High mouth opening
                crying_indicators.append("mouth_open")
    
    combined["crying_indicators"] = crying_indicators
    combined["likely_crying"] = len(crying_indicators) >= 1
    
    # Face-down detection
    if face_mesh_result and isinstance(face_mesh_result, dict):
        combined["face_down_risk"] = face_mesh_result.get("face_down_detected", False)
    else:
        combined["face_down_risk"] = False
    
    return combined


@router.post("/frames/")
async def upload_frame(file: UploadFile = File(...)):
    """
    Upload and analyze a frame from the baby monitor using LangGraph workflow.
    
    Args:
        file: Uploaded image file (required)
    
    Returns:
        JSON with workflow results including analysis, decision, alerts, and log IDs
    
    Note:
        Audio upload support is currently disabled. To enable, add audio parameter
        and modify the endpoint to handle multipart form with both file and audio.
    """
    try:
        # Read image file bytes
        image_bytes = await file.read()
        
        if not image_bytes:
            raise HTTPException(status_code=400, detail="Empty file uploaded")
        
        # Validate file size (max 10MB)
        max_size = 10 * 1024 * 1024  # 10MB
        if len(image_bytes) > max_size:
            raise HTTPException(
                status_code=400,
                detail=f"File too large: {len(image_bytes)} bytes (max: {max_size})"
            )
        
        # Audio support placeholder
        # To enable audio: add 'audio: UploadFile = File(None)' parameter above
        # and uncomment the following:
        # audio_bytes = None
        # if audio:
        #     audio_bytes = await audio.read()
        #     print(f"📎 Audio file included ({len(audio_bytes)} bytes)")
        audio_bytes = None
        
        # Run the LangGraph workflow
        # Pipeline: CameraInput -> YOLO -> Pose -> Movement -> Emotion -> Azure Fusion -> Alert/Logger
        print(f"\n🚀 Triggering LangGraph workflow for frame analysis...")
        
        workflow_result = await run_blocking(
            run_workflow,
            frame_bytes=image_bytes,
            audio_bytes=audio_bytes
        )
        
        # Map workflow result to API response format
        decision = workflow_result.get("decision_result", {}) or {}
        fusion = workflow_result.get("fusion_result", {}) or {}
        response = {
            "status": workflow_result.get("status", "unknown"),
            "timestamp": workflow_result.get("timestamp", datetime.utcnow().isoformat()),
            "analysis": fusion,
            "agents": {
                "yolo": workflow_result.get("yolo_result"),
                "pose": workflow_result.get("pose_result"),
                "movement": workflow_result.get("movement_result"),
                "emotion": workflow_result.get("emotion_result"),
                "audio": workflow_result.get("audio_result"),
            },
            "facial_mesh_data": workflow_result.get("face_mesh_result"),
            "iris_tracking_data": workflow_result.get("iris_tracking_result"),
            "combined_facial_state": _build_combined_facial_state(
                workflow_result.get("emotion_result"),
                workflow_result.get("face_mesh_result"),
                workflow_result.get("iris_tracking_result")
            ),
            "audio": workflow_result.get("audio_result"),
            "decision": decision,
            "alert": decision.get("alert", False),
            "alert_reason": decision.get("reason"),
            "alert_sent": workflow_result.get("alert_result", {}).get("sent", False),
            "alert_payload": workflow_result.get("alert_result"),
            "log_ids": workflow_result.get("log_ids", {}),
            "errors": workflow_result.get("errors", []),
        }
        response["log_id"] = response["log_ids"].get("frame_log_id")
        
        return JSONResponse(content=response)
    
    except HTTPException:
        raise  # Re-raise HTTP exceptions
    
    except Exception as e:
        print(f"❌ Error processing frame: {e}")
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")


@router.post("/frames/with-audio/")
async def upload_frame_with_audio(
    file: UploadFile = File(...),
    audio: UploadFile = File(...)
):
    """
    Upload and analyze a frame with audio from the baby monitor using LangGraph workflow.
    
    This endpoint requires BOTH image and audio files.
    
    Args:
        file: Uploaded image file (required)
        audio: Uploaded audio file (required)
    
    Returns:
        JSON with workflow results including analysis, decision, alerts, and log IDs
    """
    try:
        # Read image file bytes
        image_bytes = await file.read()
        
        if not image_bytes:
            raise HTTPException(status_code=400, detail="Empty image file uploaded")
        
        # Validate file size (max 10MB)
        max_size = 10 * 1024 * 1024  # 10MB
        if len(image_bytes) > max_size:
            raise HTTPException(
                status_code=400,
                detail=f"Image too large: {len(image_bytes)} bytes (max: {max_size})"
            )
        
        # Read audio file bytes
        audio_bytes = await audio.read()
        
        if not audio_bytes:
            raise HTTPException(status_code=400, detail="Empty audio file uploaded")
        
        if len(audio_bytes) > max_size:
            raise HTTPException(
                status_code=400,
                detail=f"Audio too large: {len(audio_bytes)} bytes (max: {max_size})"
            )
        
        print(f"📎 Audio file included ({len(audio_bytes)} bytes)")
        
        # Run the LangGraph workflow
        print(f"\n🚀 Triggering LangGraph workflow for frame + audio analysis...")
        
        workflow_result = await run_blocking(
            run_workflow,
            frame_bytes=image_bytes,
            audio_bytes=audio_bytes
        )
        
        # Map workflow result to API response format
        decision = workflow_result.get("decision_result", {}) or {}
        fusion = workflow_result.get("fusion_result", {}) or {}
        response = {
            "status": workflow_result.get("status", "unknown"),
            "timestamp": workflow_result.get("timestamp", datetime.utcnow().isoformat()),
            "analysis": fusion,
            "agents": {
                "yolo": workflow_result.get("yolo_result"),
                "pose": workflow_result.get("pose_result"),
                "movement": workflow_result.get("movement_result"),
                "emotion": workflow_result.get("emotion_result"),
                "audio": workflow_result.get("audio_result"),
            },
            "facial_mesh_data": workflow_result.get("face_mesh_result"),
            "iris_tracking_data": workflow_result.get("iris_tracking_result"),
            "combined_facial_state": _build_combined_facial_state(
                workflow_result.get("emotion_result"),
                workflow_result.get("face_mesh_result"),
                workflow_result.get("iris_tracking_result")
            ),
            "audio": workflow_result.get("audio_result"),
            "decision": decision,
            "alert": decision.get("alert", False),
            "alert_reason": decision.get("reason"),
            "alert_sent": workflow_result.get("alert_result", {}).get("sent", False),
            "alert_payload": workflow_result.get("alert_result"),
            "log_ids": workflow_result.get("log_ids", {}),
            "errors": workflow_result.get("errors", []),
        }
        response["log_id"] = response["log_ids"].get("frame_log_id")
        
        return JSONResponse(content=response)
    
    except HTTPException:
        raise  # Re-raise HTTP exceptions
    
    except Exception as e:
        print(f"❌ Error processing frame with audio: {e}")
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")


@router.get("/alerts/")
async def get_alerts(limit: int = Query(default=50, ge=1, le=500)):
    """
    Get recent alert logs from the database.
    
    Args:
        limit: Maximum number of alerts to return (1-500, default: 50)
    
    Returns:
        JSON with list of recent alerts
    """
    try:
        def fetch_alerts():
            with get_session() as session:
                statement = (
                    select(AlertLog)
                    .order_by(AlertLog.timestamp.desc())
                    .limit(limit)
                )
                alerts = session.exec(statement).all()
                
                # Convert to dict for JSON serialization
                return [
                    {
                        "id": alert.id,
                        "timestamp": alert.timestamp.isoformat(),
                        "alert_type": alert.alert_type,
                        "message": alert.message,
                        "delivered": alert.delivered
                    }
                    for alert in alerts
                ]
        
        alerts = await run_blocking(fetch_alerts)
        
        return {
            "status": "success",
            "count": len(alerts),
            "alerts": alerts
        }
    
    except Exception as e:
        print(f"❌ Error fetching alerts: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to fetch alerts: {str(e)}")


@router.get("/logs/")
async def get_logs(limit: int = Query(default=50, ge=1, le=500)):
    """
    Get recent frame analysis logs from the database.
    
    Args:
        limit: Maximum number of logs to return (1-500, default: 50)
    
    Returns:
        JSON with list of recent frame analysis logs
    """
    try:
        def fetch_logs():
            with get_session() as session:
                statement = (
                    select(FrameAnalysisLog)
                    .order_by(FrameAnalysisLog.timestamp.desc())
                    .limit(limit)
                )
                logs = session.exec(statement).all()
                
                # Convert to dict for JSON serialization
                return [
                    {
                        "id": log.id,
                        "timestamp": log.timestamp.isoformat(),
                        "frame_path": log.frame_path,
                        "baby_detected": log.baby_detected,
                        "movement_level": log.movement_level,
                        "position": log.position,
                        "risk": log.risk,
                        "raw_response": log.raw_response
                    }
                    for log in logs
                ]
        
        logs = await run_blocking(fetch_logs)
        
        return {
            "status": "success",
            "count": len(logs),
            "logs": logs
        }
    
    except Exception as e:
        print(f"❌ Error fetching logs: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to fetch logs: {str(e)}")


@router.get("/health/")
async def health_check():
    """
    Health check endpoint to verify API is running.
    
    Returns:
        JSON with status and timestamp
    """
    return {
        "status": "ok",
        "time": datetime.utcnow().isoformat(),
        "service": "baby-monitor-api",
        "version": "1.0.0"
    }


@router.websocket("/detections/live")
async def detections_live_websocket(websocket: WebSocket):
    """
    WebSocket endpoint for real-time detection results streaming.
    
    Continuously sends detection results (YOLO, pose, movement, emotion,
    face mesh, iris tracking, etc.) to connected clients while the camera
    stream is running.
    
    This endpoint is designed for Live Dashboard displays where real-time
    monitoring data is needed.
    
    Protocol:
        - Client connects to ws://localhost:8000/api/v1/detections/live
        - Server sends JSON messages with detection results every ~1 second
        - Message format: {
            "timestamp": "2025-12-01T12:00:00",
            "yolo": {...},
            "pose": {...},
            "movement": {...},
            "emotion": {...},
            "face_mesh": {...},
            "iris_tracking": {...},
            "combined_facial_state": {...},
            "summary": {...}
          }
        - Client can disconnect at any time
    
    Example (JavaScript):
        const ws = new WebSocket('ws://localhost:8000/api/v1/detections/live');
        ws.onmessage = (event) => {
            const data = JSON.parse(event.data);
            console.log('Detection results:', data);
            // Update dashboard UI with data.yolo, data.pose, etc.
        };
    """
    from src.detection_broadcaster import get_detection_broadcaster
    
    # Accept the WebSocket connection
    await websocket.accept()
    
    # Get the broadcaster
    broadcaster = get_detection_broadcaster(detection_interval=1.0)
    
    try:
        # Add client to broadcaster
        await broadcaster.add_client(websocket)
        
        # Keep connection alive
        while True:
            # Wait for messages from client (if any)
            # This keeps the connection open
            try:
                message = await websocket.receive_text()
                # Client can send commands if needed (not currently used)
                print(f"Received from client: {message}")
            except WebSocketDisconnect:
                break
    
    except WebSocketDisconnect:
        print("Client disconnected")
    
    except Exception as e:
        print(f"WebSocket error: {e}")
    
    finally:
        # Remove client from broadcaster
        await broadcaster.remove_client(websocket)


@router.get("/detections/latest")
async def get_latest_detections():
    """
    Get the latest detection results without WebSocket.
    
    Returns the most recent detection data from the detection broadcaster.
    Useful for polling-based clients or one-time queries.
    
    Returns:
        JSON with latest detection results or empty dict if no detections yet
    """
    from src.detection_broadcaster import get_detection_broadcaster
    
    broadcaster = get_detection_broadcaster()
    latest = broadcaster.get_latest_results()
    
    if not latest:
        return {
            "status": "no_data",
            "message": "No detection results available yet. Start the camera stream first."
        }
    
    return {
        "status": "success",
        **latest
    }


@router.get("/stream/")
async def stream_video(request: Request):
    """
    Stream live video feed in MJPEG format compatible with HTML <img> tags.
    
    This endpoint provides a continuous MJPEG stream that can be displayed
    directly in an HTML image element:
        <img src="http://localhost:8000/api/v1/stream/" />
    
    Features:
        - No authentication required
        - Thread-safe for multiple concurrent viewers
        - Efficient JPEG encoding with configurable quality
        - Automatic frame rate control
        - Handles client disconnections gracefully
    
    Returns:
        StreamingResponse: MJPEG video stream with multipart/x-mixed-replace content type
    """
    from src.camera_streamer import get_camera_streamer
    
    # Get the camera streamer instance
    streamer = get_camera_streamer()
    
    # Register this viewer
    streamer.add_viewer()
    
    # Wait a moment for camera to initialize if needed
    await asyncio.sleep(0.1)
    
    # Define boundary (must match the one in media_type)
    boundary = "----video-boundary"
    boundary_bytes = boundary.encode()
    
    async def generate_frames():
        """Generate MJPEG frames continuously."""
        settings = get_settings()
        frame_delay = 1.0 / settings.STREAM_FPS if settings.STREAM_FPS > 0 else 0.1
        
        try:
            while True:
                # Check if client disconnected
                if await request.is_disconnected():
                    break
                
                # Get latest frame
                frame_bytes = streamer.get_frame()
                
                if frame_bytes is None:
                    # No frame available yet, wait and retry
                    await asyncio.sleep(0.1)
                    continue
                
                # Send frame in MJPEG format (multipart/x-mixed-replace)
                frame_data = (
                    b"--" + boundary_bytes + b"\r\n"
                    b"Content-Type: image/jpeg\r\n"
                    b"Content-Length: " + str(len(frame_bytes)).encode() + b"\r\n\r\n"
                    + frame_bytes
                    + b"\r\n"
                )
                
                yield frame_data
                
                # Control frame rate
                await asyncio.sleep(frame_delay)
        
        except asyncio.CancelledError:
            # Client disconnected
            pass
        except Exception as e:
            print(f"Error in video stream: {e}")
        finally:
            # Unregister this viewer
            streamer.remove_viewer()
    
    return StreamingResponse(
        generate_frames(),
        media_type=f"multipart/x-mixed-replace; boundary={boundary}",
        headers={
            "Cache-Control": "no-cache, no-store, must-revalidate",
            "Pragma": "no-cache",
            "Expires": "0",
            "Connection": "keep-alive",
        }
    )


@router.get("/stream/audio/")
async def stream_audio(request: Request):
    """
    Stream live audio feed in continuous WAV format.
    
    This endpoint provides a continuous audio stream that can be played
    directly in an HTML audio element:
        <audio src="http://localhost:8000/api/v1/stream/audio/" autoplay controls></audio>
    
    Features:
        - Real-time audio streaming from microphone
        - WAV format (PCM 16-bit, mono, 16kHz)
        - Thread-safe for multiple concurrent listeners
        - Automatic start/stop based on listeners
        - Handles client disconnections gracefully
    
    Returns:
        StreamingResponse: Continuous WAV audio stream
    """
    from src.audio_streamer import get_audio_streamer
    import struct
    
    # Get the audio streamer instance
    audio_streamer = get_audio_streamer()
    
    # Check if audio is available
    if not audio_streamer.is_available():
        raise HTTPException(
            status_code=503,
            detail="Audio device not available. Please install sounddevice: pip install sounddevice"
        )
    
    # Register this listener
    audio_streamer.add_viewer()
    
    # Wait a moment for audio to initialize
    await asyncio.sleep(0.1)
    
    async def generate_audio():
        """Generate continuous WAV audio stream."""
        sample_rate = audio_streamer.get_sample_rate()
        channels = 1  # Mono
        sample_width = 2  # 16-bit
        
        # Send WAV header first
        wav_header = _create_wav_header(sample_rate, channels, sample_width)
        yield wav_header
        
        try:
            while True:
                # Check if client disconnected
                if await request.is_disconnected():
                    break
                
                # Get latest audio chunk
                audio_chunk = audio_streamer.get_latest_chunk()
                
                if audio_chunk is None:
                    # No audio available yet, wait and retry
                    await asyncio.sleep(0.1)
                    continue
                
                # Convert float32 to int16 PCM
                audio_int16 = (audio_chunk * 32767).astype(np.int16)
                
                # Convert to bytes
                audio_bytes = audio_int16.tobytes()
                
                yield audio_bytes
                
                # Small delay to control streaming rate
                await asyncio.sleep(0.1)
        
        except asyncio.CancelledError:
            # Client disconnected
            pass
        except Exception as e:
            logger.error(f"Error in audio stream: {e}")
        finally:
            # Unregister this listener
            audio_streamer.remove_viewer()
    
    return StreamingResponse(
        generate_audio(),
        media_type="audio/wav",
        headers={
            "Cache-Control": "no-cache, no-store, must-revalidate",
            "Pragma": "no-cache",
            "Expires": "0",
            "Connection": "keep-alive",
        }
    )


def _create_wav_header(sample_rate: int, channels: int, sample_width: int) -> bytes:
    """
    Create a WAV file header for streaming audio.
    
    Args:
        sample_rate: Sample rate in Hz
        channels: Number of audio channels (1=mono, 2=stereo)
        sample_width: Sample width in bytes (2=16-bit, 4=32-bit)
    
    Returns:
        WAV header bytes (44 bytes)
    """
    import struct
    
    # WAV header format (44 bytes total)
    # We use a large data size since it's a stream
    data_size = 0xFFFFFFFF - 36  # Maximum size for infinite stream
    
    header = struct.pack('<4sI4s', b'RIFF', data_size + 36, b'WAVE')
    header += struct.pack('<4sIHHIIHH',
        b'fmt ',  # Chunk ID
        16,  # Chunk size (16 for PCM)
        1,  # Audio format (1 = PCM)
        channels,  # Number of channels
        sample_rate,  # Sample rate
        sample_rate * channels * sample_width,  # Byte rate
        channels * sample_width,  # Block align
        sample_width * 8  # Bits per sample
    )
    header += struct.pack('<4sI', b'data', data_size)
    
    return header


@router.get("/stream/annotated/")
async def stream_annotated_video(request: Request):
    """
    Stream live video feed with detection visualizations overlaid.
    
    This endpoint provides a continuous MJPEG stream with:
    - Bounding boxes around detected babies and adults
    - Pose estimation skeleton (green lines)
    - Face mesh landmarks (magenta lines)
    - Iris tracking (cyan markers)
    - Status overlay with emotion, pose, and alerts
    
    Display in HTML:
        <img src="http://localhost:8000/api/v1/stream/annotated/" />
    
    Features:
        - Real-time detection visualizations
        - Thread-safe for multiple concurrent viewers
        - Automatic frame rate control
        - Handles client disconnections gracefully
    
    Returns:
        StreamingResponse: MJPEG video stream with detection overlays
    """
    from src.annotated_video_streamer import get_annotated_streamer
    
    # Get the annotated streamer instance
    streamer = get_annotated_streamer()
    
    # Register this viewer
    streamer.add_viewer()
    
    # Wait a moment for initialization
    await asyncio.sleep(0.2)
    
    # Define boundary
    boundary = "----annotated-video-boundary"
    boundary_bytes = boundary.encode()
    
    async def generate_frames():
        """Generate MJPEG frames with annotations."""
        # NOTE: Don't add delay here - the annotated streamer already controls frame rate
        # Adding delay here causes double-buffering and increases lag
        
        try:
            while True:
                # Check if client disconnected
                if await request.is_disconnected():
                    break
                
                # Get latest annotated frame
                frame_bytes = streamer.get_frame()
                
                if frame_bytes is None:
                    # No frame available yet, wait briefly and retry
                    await asyncio.sleep(0.05)  # Short wait only when no frame available
                    continue
                
                # Send frame in MJPEG format
                frame_data = (
                    b"--" + boundary_bytes + b"\r\n"
                    b"Content-Type: image/jpeg\r\n"
                    b"Content-Length: " + str(len(frame_bytes)).encode() + b"\r\n\r\n"
                    + frame_bytes
                    + b"\r\n"
                )
                
                yield frame_data
                
                # Small yield to prevent CPU spinning, but don't add frame delay
                # The annotation loop already controls the frame rate
                await asyncio.sleep(0.01)  # Just yield CPU, not rate limiting
        
        except asyncio.CancelledError:
            pass
        except Exception as e:
            print(f"Error in annotated video stream: {e}")
        finally:
            # Unregister this viewer
            streamer.remove_viewer()
    
    return StreamingResponse(
        generate_frames(),
        media_type=f"multipart/x-mixed-replace; boundary={boundary}",
        headers={
            "Cache-Control": "no-cache, no-store, must-revalidate",
            "Pragma": "no-cache",
            "Expires": "0",
            "Connection": "keep-alive",
        }
    )


@router.get("/stats/")
async def get_stats():
    """
    Get statistics about the monitoring system.
    
    Returns:
        JSON with system statistics
    """
    try:
        def fetch_stats():
            with get_session() as session:
                # Count total logs
                total_frames = session.exec(
                    select(FrameAnalysisLog)
                ).all()
                
                total_alerts = session.exec(
                    select(AlertLog)
                ).all()
                
                # Count alerts in last 24 hours
                from datetime import timedelta
                cutoff = datetime.utcnow() - timedelta(hours=24)
                
                recent_alerts = [a for a in total_alerts if a.timestamp >= cutoff]
                recent_frames = [f for f in total_frames if f.timestamp >= cutoff]
                
                # Count baby detected
                baby_detected_count = sum(1 for f in total_frames if f.baby_detected)
                
                # Count by risk level
                risk_counts = {}
                for frame in total_frames:
                    risk = frame.risk or "unknown"
                    risk_counts[risk] = risk_counts.get(risk, 0) + 1
                
                return {
                    "total_frames_analyzed": len(total_frames),
                    "total_alerts_sent": len(total_alerts),
                    "frames_last_24h": len(recent_frames),
                    "alerts_last_24h": len(recent_alerts),
                    "baby_detected_count": baby_detected_count,
                    "risk_level_distribution": risk_counts
                }
        
        stats = await run_blocking(fetch_stats)
        
        return {
            "status": "success",
            "timestamp": datetime.utcnow().isoformat(),
            "stats": stats
        }
    
    except Exception as e:
        print(f"❌ Error fetching stats: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to fetch stats: {str(e)}")


# Optional: Add CORS middleware configuration
def configure_cors(app):
    """
    Configure CORS for the application.
    Call this from main.py if needed.
    """
    from fastapi.middleware.cors import CORSMiddleware
    
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],  # In production, specify actual origins
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )


# ==============================================================================
# CHATBOT RAG ENDPOINTS
# ==============================================================================

@router.post("/chatbot/ask")
async def chatbot_ask(request: dict):
    """
    Ask the Lalla Care chatbot a question using LangGraph RAG workflow.
    
    The chatbot uses LangGraph with conditional edges to intelligently route questions:
    - Questions about Lalla Care → RAG retrieval from documentation
    - Out-of-scope questions → General LLM response
    
    This endpoint now uses the advanced LangGraph implementation with conversation history.
    
    Args:
        request: JSON with 'question' and optional 'thread_id' fields
        
    Request Body:
        {
            "question": "How do I connect my camera?",
            "thread_id": "user-123"  // optional
        }
    
    Returns:
        JSON response with answer and metadata
        
    Response Body:
        {
            "answer": "To connect your camera...",
            "question": "How do I connect my camera?",
            "routing": "rag",
            "thread_id": "user-123",
            "has_context": true,
            "processing_time_seconds": 1.23,
            "timestamp": "2024-01-01T12:00:00"
        }
    """
    try:
        from src.langgraph_rag_chatbot import ask_chatbot_langgraph
        
        # Validate request
        if not request or "question" not in request:
            raise HTTPException(
                status_code=400, 
                detail="Request must include 'question' field"
            )
        
        question = request.get("question", "").strip()
        thread_id = request.get("thread_id")
        
        if not question:
            raise HTTPException(
                status_code=400,
                detail="Question cannot be empty"
            )
        
        if len(question) > 1000:
            raise HTTPException(
                status_code=400,
                detail="Question too long (max 1000 characters)"
            )
        
        # Log incoming question
        print(f"\n💬 Chatbot Question: {question}")
        if thread_id:
            print(f"   Thread ID: {thread_id}")
        
        # Process question through LangGraph RAG pipeline
        result = await ask_chatbot_langgraph(question, thread_id)
        
        # Log answer
        print(f"✅ Chatbot Answer ({result.get('routing', 'unknown')}): {result.get('answer', '')[:100]}...")
        
        return JSONResponse(content=result)
    
    except HTTPException:
        raise
    
    except Exception as e:
        print(f"❌ Error in chatbot endpoint: {e}")
        import traceback
        traceback.print_exc()
        raise HTTPException(
            status_code=500,
            detail=f"Chatbot error: {str(e)}"
        )


@router.post("/chatbot/rebuild_index")
async def chatbot_rebuild_index():
    """
    Rebuild the RAG index from scratch using LangGraph implementation.
    
    This endpoint will:
    1. Re-read the Lalla Care PDF from rag_document/ folder
    2. Split document into chunks with metadata
    3. Generate embeddings using HuggingFace model
    4. Build FAISS vector store index
    5. Save index to disk
    
    Use this endpoint when:
    - The PDF document has been updated
    - Index is corrupted or missing
    - You want to refresh the index
    
    Returns:
        JSON with rebuild statistics and status
        
    Response Body:
        {
            "status": "success",
            "build_time_seconds": 5.23,
            "timestamp": "2024-01-01T12:00:00"
        }
    """
    try:
        from src.langgraph_rag_chatbot import rebuild_index_langgraph
        
        print("\n🔄 Rebuilding LangGraph RAG index...")
        
        # Run rebuild in blocking mode
        stats = await run_blocking(rebuild_index_langgraph)
        
        print(f"✅ LangGraph index rebuilt successfully")
        
        return JSONResponse(content=stats)
    
    except FileNotFoundError as e:
        print(f"❌ File not found: {e}")
        raise HTTPException(
            status_code=404,
            detail=f"PDF document not found: {str(e)}"
        )
    
    except Exception as e:
        print(f"❌ Error rebuilding index: {e}")
        import traceback
        traceback.print_exc()
        raise HTTPException(
            status_code=500,
            detail=f"Failed to rebuild index: {str(e)}"
        )


@router.get("/chatbot/status")
async def chatbot_status():
    """
    Get the status of the LangGraph RAG chatbot system.
    
    Returns information about whether the index is built and ready to use.
    
    Returns:
        JSON with status information
        
    Response Body (when ready):
        {
            "status": "ready",
            "pdf_exists": true,
            "pdf_path": "...",
            "index_exists": true,
            "index_path": "...",
            "database_path": "...",
            "threads_count": 5
        }
        
    Response Body (when not ready):
        {
            "status": "not_ready",
            "pdf_exists": false,
            "index_exists": false
        }
    """
    try:
        from src.langgraph_rag_chatbot import check_status_langgraph
        
        status = check_status_langgraph()
        
        return JSONResponse(content=status)
    
    except Exception as e:
        print(f"❌ Error checking chatbot status: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to check status: {str(e)}"
        )


# ==============================================================================
# LANGGRAPH RAG CHATBOT ENDPOINTS
# ==============================================================================

@router.post("/chatbot/langgraph/ask")
async def chatbot_langgraph_ask(request: dict):
    """
    Ask the LangGraph-based RAG chatbot a question.
    
    This chatbot uses LangGraph with conditional edges to route questions:
    - Questions about Lalla Care -> RAG retrieval from documentation
    - Out-of-scope questions -> General LLM response
    
    Args:
        request: JSON with 'question' and optional 'thread_id' fields
        
    Request Body:
        {
            "question": "How do I set up the camera?",
            "thread_id": "user-123"  // optional, for conversation history
        }
    
    Returns:
        JSON response with answer and metadata
        
    Response Body:
        {
            "answer": "To set up the camera...",
            "question": "How do I set up the camera?",
            "routing": "rag",  // or "general"
            "thread_id": "user-123",
            "has_context": true,
            "processing_time_seconds": 1.23,
            "timestamp": "2024-01-01T12:00:00"
        }
    """
    try:
        from src.langgraph_rag_chatbot import ask_chatbot_langgraph
        
        # Validate request
        if not request or "question" not in request:
            raise HTTPException(
                status_code=400, 
                detail="Request must include 'question' field"
            )
        
        question = request.get("question", "").strip()
        thread_id = request.get("thread_id")
        
        if not question:
            raise HTTPException(
                status_code=400,
                detail="Question cannot be empty"
            )
        
        if len(question) > 1000:
            raise HTTPException(
                status_code=400,
                detail="Question too long (max 1000 characters)"
            )
        
        # Log incoming question
        print(f"\n💬 LangGraph Chatbot Question: {question}")
        if thread_id:
            print(f"   Thread ID: {thread_id}")
        
        # Process question through LangGraph RAG pipeline
        result = await ask_chatbot_langgraph(question, thread_id)
        
        # Log answer
        print(f"✅ LangGraph Answer ({result.get('routing', 'unknown')}): {result.get('answer', '')[:100]}...")
        
        return JSONResponse(content=result)
    
    except HTTPException:
        raise
    
    except Exception as e:
        print(f"❌ Error in LangGraph chatbot endpoint: {e}")
        import traceback
        traceback.print_exc()
        raise HTTPException(
            status_code=500,
            detail=f"LangGraph chatbot error: {str(e)}"
        )


@router.post("/chatbot/langgraph/rebuild_index")
async def chatbot_langgraph_rebuild():
    """
    Rebuild the FAISS index for the LangGraph chatbot.
    
    This will re-process the Lalla Care PDF and create a new vector store.
    
    Returns:
        JSON with rebuild statistics
        
    Response Body:
        {
            "status": "success",
            "build_time_seconds": 5.23,
            "timestamp": "2024-01-01T12:00:00"
        }
    """
    try:
        from src.langgraph_rag_chatbot import rebuild_index_langgraph
        
        print("\n🔄 Rebuilding LangGraph RAG index...")
        
        # Run rebuild
        stats = await run_blocking(rebuild_index_langgraph)
        
        print(f"✅ LangGraph index rebuilt successfully")
        
        return JSONResponse(content=stats)
    
    except FileNotFoundError as e:
        print(f"❌ File not found: {e}")
        raise HTTPException(
            status_code=404,
            detail=f"PDF document not found: {str(e)}"
        )
    
    except Exception as e:
        print(f"❌ Error rebuilding LangGraph index: {e}")
        import traceback
        traceback.print_exc()
        raise HTTPException(
            status_code=500,
            detail=f"Failed to rebuild index: {str(e)}"
        )


@router.get("/chatbot/langgraph/status")
async def chatbot_langgraph_status():
    """
    Get the status of the LangGraph RAG chatbot system.
    
    Returns:
        JSON with status information
        
    Response Body:
        {
            "status": "ready",
            "pdf_exists": true,
            "pdf_path": "...",
            "index_exists": true,
            "index_path": "...",
            "database_path": "...",
            "threads_count": 5
        }
    """
    try:
        from src.langgraph_rag_chatbot import check_status_langgraph
        
        status = check_status_langgraph()
        
        return JSONResponse(content=status)
    
    except Exception as e:
        print(f"❌ Error checking LangGraph status: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to check status: {str(e)}"
        )


@router.get("/chatbot/langgraph/threads")
async def chatbot_langgraph_threads():
    """
    Get all conversation thread IDs for the LangGraph chatbot.
    
    Returns:
        JSON with list of thread IDs
        
    Response Body:
        {
            "threads": ["user-123", "user-456", "default"],
            "count": 3
        }
    """
    try:
        from src.langgraph_rag_chatbot import get_all_threads
        
        threads = get_all_threads()
        
        return JSONResponse(content={
            "threads": threads,
            "count": len(threads)
        })
    
    except Exception as e:
        print(f"❌ Error fetching threads: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to fetch threads: {str(e)}"
        )