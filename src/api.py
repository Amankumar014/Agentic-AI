"""
FastAPI router for baby monitor API endpoints.
Provides endpoints for frame upload, analysis, alerts, and logs.
"""
import json
from datetime import datetime
from typing import List, Optional

from fastapi import APIRouter, UploadFile, File, Query, HTTPException
from starlette.requests import Request
from fastapi.responses import JSONResponse, StreamingResponse
from sqlmodel import select
import asyncio

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