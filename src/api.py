"""
FastAPI router for baby monitor API endpoints.
Provides endpoints for frame upload, analysis, alerts, and logs.
"""
import json
from datetime import datetime
from typing import List, Optional

from fastapi import APIRouter, UploadFile, File, Query, HTTPException
from fastapi.responses import JSONResponse
from sqlmodel import select

from src.config import get_settings
from src.models import get_session, FrameAnalysisLog, AlertLog
from src.langgraph_workflow import run as run_workflow
from src.utils import run_blocking


# Create API router
router = APIRouter()


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
