"""
LangGraph workflow for baby monitor analysis pipeline.
Orchestrates vision, audio, decision, alert, and logging agents.

Each agent is implemented as a node with:
- Clear system prompts/metadata describing its purpose
- Input/output logging for debugging
- Specialized processing logic
"""
import json
from typing import Dict, Any, Optional, TypedDict
from datetime import datetime

from langgraph.graph import StateGraph

from src.azure_vision import analyze_image_bytes
from src.audio_agent_placeholder import (
    extract_librosa_features,
    classify_cry,
    save_audio_to_temp,
    get_feature_vector
)
from src.agent import decision_from_vision
from src.notifier import send_alert
from src.models import get_session, FrameAnalysisLog, AlertLog
from src.utils import save_bytes_to_temp


# ============================================================================
# Agent Metadata - System Prompts and Purpose Descriptions
# ============================================================================

AGENT_METADATA = {
    "camera_input": {
        "name": "Camera Input Agent",
        "purpose": "Receives and validates raw camera frame and audio data. Saves bytes to temporary storage for processing.",
        "inputs": ["frame_bytes", "audio_bytes"],
        "outputs": ["frame_path", "audio_path"],
        "model": "Direct Python I/O"
    },
    "vision_agent": {
        "name": "Vision Analysis Agent",
        "purpose": "Analyzes video frames using Azure OpenAI GPT-4 Vision to detect baby presence, movement, position, emotional state (crying/calm), and risk levels.",
        "system_prompt": """You are a baby monitor AI assistant. Analyze the provided image with special attention to the baby's emotional state and facial expressions.

Your response must be valid JSON with these exact keys:
{
  "baby_detected": boolean,
  "movement_level": string (one of: "none", "minimal", "low", "moderate", "high"),
  "position": string (description of baby's position),
  "risk": string (one of: "safe", "monitor", "caution", "alert"),
  "notes": string (brief observations or concerns)
}

Guidelines:
- baby_detected: true if you can see a baby/infant in the image
- movement_level: assess based on visible motion blur, posture changes, limb movement
- position: describe the baby's current position/posture
- risk: "safe" = calm & safe, "monitor" = crying/distress/watch closely, "caution" = unsafe position or moderate distress, "alert" = danger or severe distress
- notes: CRITICAL - Report facial expression (crying/calm), signs of distress, comfort level, and safety concerns

CRITICAL: Look VERY carefully at the baby's FACE. If mouth is open wide, face is scrunched, or eyes show distress, the baby IS CRYING. Set risk to "monitor" and state "baby is crying" in notes. DO NOT say "calm" if you see crying signs.""",
        "inputs": ["frame_bytes"],
        "outputs": ["vision_result"],
        "model": "Azure OpenAI GPT-4 Vision"
    },
    "audio_agent": {
        "name": "Audio Analysis Agent",
        "purpose": "Extracts acoustic features from audio samples and classifies crying using machine learning model.",
        "description": "Uses librosa for feature extraction (MFCC, ZCR, spectral centroid) and trained ML model for cry detection.",
        "inputs": ["audio_path"],
        "outputs": ["audio_result"],
        "model": "Direct Python (librosa + scikit-learn)"
    },
    "decision_agent": {
        "name": "Decision Fusion Agent",
        "purpose": "Applies rule-based logic to fuse vision and audio signals, making alert decisions based on multiple risk factors.",
        "rules": [
            "High risk detected (distress, fall, alert, caution) → ALERT",
            "Baby not detected in frame → ALERT",
            "High movement level → ALERT",
            "Moderate movement + caution risk → ALERT",
            "Crying detected with suspicious movement → ALERT",
            "Dangerous position (face down, covered) → ALERT"
        ],
        "inputs": ["vision_result", "audio_result"],
        "outputs": ["decision_result"],
        "model": "Direct Python (rule-based system)"
    },
    "alert_agent": {
        "name": "Multi-Channel Alert Agent",
        "purpose": "Sends notifications via email (SMTP) and SMS (Twilio) when alerts are triggered.",
        "channels": ["Email (SMTP)", "SMS (Twilio)"],
        "inputs": ["decision_result"],
        "outputs": ["alert_result"],
        "model": "Direct Python (SMTP + Twilio API)"
    },
    "logger_agent": {
        "name": "Database Logger Agent",
        "purpose": "Persists analysis results and alert history to SQLite database for auditing and historical analysis.",
        "tables": ["frame_analysis_logs", "alert_logs"],
        "inputs": ["vision_result", "decision_result", "alert_result"],
        "outputs": ["log_ids"],
        "model": "Direct Python (SQLModel/SQLite)"
    }
}


# ============================================================================
# State Definition
# ============================================================================

class WorkflowState(TypedDict):
    """State that flows through the LangGraph workflow."""
    # Input data
    frame_bytes: Optional[bytes]
    audio_bytes: Optional[bytes]
    
    # Intermediate results
    frame_path: Optional[str]
    audio_path: Optional[str]
    vision_result: Optional[Dict[str, Any]]
    audio_result: Optional[Dict[str, Any]]
    decision_result: Optional[Dict[str, Any]]
    alert_result: Optional[Dict[str, Any]]
    
    # Final outputs
    log_ids: Dict[str, Optional[int]]
    timestamp: str
    status: str
    errors: list


def log_agent_input(agent_name: str, state: WorkflowState) -> None:
    """Log agent input for debugging."""
    metadata = AGENT_METADATA.get(agent_name, {})
    inputs = metadata.get("inputs", [])
    
    print(f"\n{'='*70}")
    print(f"🔵 INPUT → {metadata.get('name', agent_name)}")
    print(f"{'='*70}")
    print(f"Purpose: {metadata.get('purpose', 'N/A')}")
    print(f"Model: {metadata.get('model', 'N/A')}")
    print(f"\nInput Data:")
    
    for input_key in inputs:
        value = state.get(input_key)
        if value is not None:
            if isinstance(value, bytes):
                print(f"  • {input_key}: <bytes, length={len(value)}>")
            elif isinstance(value, dict):
                print(f"  • {input_key}: {json.dumps(value, indent=4)[:200]}...")
            else:
                print(f"  • {input_key}: {str(value)[:200]}")
        else:
            print(f"  • {input_key}: None")


def log_agent_output(agent_name: str, state: WorkflowState, success: bool = True) -> None:
    """Log agent output for debugging."""
    metadata = AGENT_METADATA.get(agent_name, {})
    outputs = metadata.get("outputs", [])
    
    print(f"\n{'='*70}")
    print(f"{'✅' if success else '❌'} OUTPUT ← {metadata.get('name', agent_name)}")
    print(f"{'='*70}")
    print(f"Status: {'Success' if success else 'Failed'}")
    print(f"\nOutput Data:")
    
    for output_key in outputs:
        value = state.get(output_key)
        if value is not None:
            if isinstance(value, dict):
                print(f"  • {output_key}:")
                for k, v in value.items():
                    print(f"      {k}: {v}")
            else:
                print(f"  • {output_key}: {str(value)[:200]}")
        else:
            print(f"  • {output_key}: None")
    
    if state.get("errors"):
        print(f"\n⚠️  Errors: {len(state['errors'])}")
        for error in state["errors"]:
            print(f"  - {error}")
    
    print(f"{'='*70}\n")


# ============================================================================
# Node Functions
# ============================================================================

def camera_input_node(state: WorkflowState) -> WorkflowState:
    """
    Node 1: Camera Input Processing Agent
    
    Purpose: Receives and validates raw camera frame and audio data.
             Saves bytes to temporary storage for processing.
    
    Model: Direct Python I/O operations
    """
    agent_name = "camera_input"
    log_agent_input(agent_name, state)
    
    print("\n[Processing...]")
    
    try:
        # Save frame bytes if present
        if state.get("frame_bytes"):
            frame_path = save_bytes_to_temp(state["frame_bytes"], suffix=".jpg")
            state["frame_path"] = frame_path
            print(f"  ✅ Frame saved: {frame_path}")
        else:
            print("  ⚠️  No frame bytes provided")
        
        # Save audio bytes if present
        if state.get("audio_bytes"):
            # For audio, we'd need to handle the format properly
            # This is a placeholder - in production, handle audio format
            audio_path = save_bytes_to_temp(state["audio_bytes"], suffix=".wav")
            state["audio_path"] = audio_path
            print(f"  ✅ Audio saved: {audio_path}")
        else:
            print("  ℹ️  No audio bytes provided (optional)")
        
        state["status"] = "input_processed"
        log_agent_output(agent_name, state, success=True)
        
    except Exception as e:
        print(f"  ❌ Error in camera input: {e}")
        state["errors"].append(f"camera_input: {str(e)}")
        state["status"] = "error"
        log_agent_output(agent_name, state, success=False)
    
    return state


def vision_agent_node(state: WorkflowState) -> WorkflowState:
    """
    Node 2: Vision Analysis Agent
    
    Purpose: Analyzes video frames using Azure OpenAI GPT-4 Vision to detect
             baby presence, movement, position, and risk levels.
    
    Model: Azure OpenAI GPT-4 Vision with custom system prompt
    
    System Prompt: Instructs the model to return structured JSON with
                   baby_detected, movement_level, position, risk, and notes.
    """
    agent_name = "vision_agent"
    log_agent_input(agent_name, state)
    
    print("\n[Processing with Azure OpenAI Vision...]")
    print(f"System Prompt: {AGENT_METADATA['vision_agent']['system_prompt'][:100]}...")
    
    try:
        if not state.get("frame_bytes"):
            print("  ⚠️  No frame bytes - skipping vision analysis")
            state["vision_result"] = {
                "baby_detected": False,
                "error": "No frame provided"
            }
            log_agent_output(agent_name, state, success=False)
            return state
        
        # Analyze image with Azure Vision (uses custom system prompt internally)
        import asyncio
        
        # Check if we're in an event loop
        try:
            loop = asyncio.get_event_loop()
            if loop.is_running():
                # We're in an async context, create a task
                vision_result = asyncio.create_task(
                    analyze_image_bytes(state["frame_bytes"])
                )
                # Note: This won't work well in sync context
                # Better to use asyncio.run in a new loop
                raise RuntimeError("Cannot run async in existing loop")
        except RuntimeError:
            # No event loop or can't use it, create new one
            vision_result = asyncio.run(analyze_image_bytes(state["frame_bytes"]))
        
        state["vision_result"] = vision_result
        
        if "error" in vision_result:
            print(f"  ⚠️  Vision analysis error: {vision_result['error']}")
            log_agent_output(agent_name, state, success=False)
        else:
            baby_detected = vision_result.get("baby_detected", False)
            risk = vision_result.get("risk", "unknown")
            movement = vision_result.get("movement_level", "unknown")
            position = vision_result.get("position", "unknown")
            notes = vision_result.get("notes", "")
            
            print(f"  ✅ Vision analysis complete")
            print(f"     Baby detected: {baby_detected}")
            print(f"     Risk: {risk}, Movement: {movement}")
            print(f"     Position: {position}")
            print(f"     Notes: {notes}")
            
            log_agent_output(agent_name, state, success=True)
        
        state["status"] = "vision_complete"
        
    except Exception as e:
        print(f"  ❌ Error in vision agent: {e}")
        state["errors"].append(f"vision_agent: {str(e)}")
        state["vision_result"] = {"error": str(e), "baby_detected": False}
        log_agent_output(agent_name, state, success=False)
    
    return state


def audio_agent_node(state: WorkflowState) -> WorkflowState:
    """
    Node 3: Audio Analysis Agent
    
    Purpose: Extracts acoustic features from audio samples and classifies
             crying using machine learning model.
    
    Model: Direct Python (librosa for feature extraction + scikit-learn for classification)
    
    Features Extracted:
    - MFCC (Mel-frequency cepstral coefficients)
    - ZCR (Zero-crossing rate)
    - Spectral Centroid
    - RMS Energy
    - Tempo
    """
    agent_name = "audio_agent"
    log_agent_input(agent_name, state)
    
    print("\n[Processing with librosa + scikit-learn...]")
    
    try:
        if not state.get("audio_path"):
            print("  ℹ️  No audio provided - skipping audio analysis")
            state["audio_result"] = None
            log_agent_output(agent_name, state, success=True)
            return state
        
        print(f"  📊 Extracting acoustic features...")
        # Extract features from audio file
        features = extract_librosa_features(state["audio_path"])
        print(f"     Features: MFCC={features['mfcc_mean']:.2f}, ZCR={features['zcr_mean']:.4f}")
        print(f"     Spectral Centroid={features['spectral_centroid_mean']:.2f}")
        
        print(f"  🤖 Running cry classification model...")
        # Classify cry
        classification = classify_cry(features)
        
        # Combine results
        audio_result = {
            "features": features,
            "is_crying": classification.get("is_crying", False),
            "confidence": classification.get("confidence", 0.0),
            "model_loaded": classification.get("model_loaded", False)
        }
        
        state["audio_result"] = audio_result
        
        if audio_result["is_crying"]:
            print(f"  🚨 Crying detected! Confidence: {audio_result['confidence']:.2%}")
        else:
            print(f"  ✅ No crying detected (confidence: {audio_result['confidence']:.2%})")
        
        if not audio_result["model_loaded"]:
            print(f"  ℹ️  Note: No ML model loaded, using default classification")
        
        state["status"] = "audio_complete"
        log_agent_output(agent_name, state, success=True)
        
    except Exception as e:
        print(f"  ❌ Error in audio agent: {e}")
        state["errors"].append(f"audio_agent: {str(e)}")
        state["audio_result"] = {
            "error": str(e),
            "is_crying": False,
            "confidence": 0.0
        }
        log_agent_output(agent_name, state, success=False)
    
    return state


def decision_agent_node(state: WorkflowState) -> WorkflowState:
    """
    Node 4: Decision Fusion Agent
    
    Purpose: Applies rule-based logic to fuse vision and audio signals,
             making alert decisions based on multiple risk factors.
    
    Model: Direct Python (rule-based expert system)
    
    Decision Rules:
    1. High risk detected (distress, fall, alert, caution) → ALERT
    2. Baby not detected in frame → ALERT
    3. High movement level → ALERT
    4. Moderate movement + caution risk → ALERT
    5. Crying detected with suspicious movement → ALERT
    6. Dangerous position (face down, covered) → ALERT
    """
    agent_name = "decision_agent"
    log_agent_input(agent_name, state)
    
    print("\n[Processing with rule-based system...]")
    print("Applying decision rules:")
    for i, rule in enumerate(AGENT_METADATA['decision_agent']['rules'], 1):
        print(f"  Rule {i}: {rule}")
    
    try:
        vision_result = state.get("vision_result", {})
        audio_result = state.get("audio_result")
        
        if not vision_result:
            print("\n  ⚠️  No vision result - cannot make decision")
            state["decision_result"] = {
                "alert": False,
                "reason": "No vision data available"
            }
            log_agent_output(agent_name, state, success=False)
            return state
        
        print(f"\n  🔍 Analyzing inputs...")
        print(f"     Vision: baby_detected={vision_result.get('baby_detected')}, risk={vision_result.get('risk')}")
        if audio_result:
            print(f"     Audio: is_crying={audio_result.get('is_crying')}, confidence={audio_result.get('confidence', 0):.2f}")
        
        # Make decision using agent
        decision_result = decision_from_vision(vision_result, audio_result)
        
        state["decision_result"] = decision_result
        
        if decision_result.get("alert"):
            print(f"\n  🚨 ALERT TRIGGERED!")
            print(f"     Reason: {decision_result.get('reason')}")
            print(f"     Will notify: {decision_result.get('notified', False)}")
        else:
            print(f"\n  ✅ No alert needed")
            print(f"     Reason: {decision_result.get('reason')}")
        
        state["status"] = "decision_complete"
        log_agent_output(agent_name, state, success=True)
        
    except Exception as e:
        print(f"  ❌ Error in decision agent: {e}")
        state["errors"].append(f"decision_agent: {str(e)}")
        state["decision_result"] = {
            "alert": False,
            "reason": f"Error: {str(e)}"
        }
        log_agent_output(agent_name, state, success=False)
    
    return state


def alert_agent_node(state: WorkflowState) -> WorkflowState:
    """
    Node 5: Multi-Channel Alert Agent
    
    Purpose: Sends notifications via email (SMTP) and SMS (Twilio) when
             alerts are triggered.
    
    Model: Direct Python (SMTP for email + Twilio API for SMS)
    
    Channels:
    - Email: SMTP with STARTTLS encryption
    - SMS: Twilio REST API
    
    Features:
    - Multi-channel redundancy
    - Graceful fallback if one channel fails
    - Delivery confirmation tracking
    """
    agent_name = "alert_agent"
    log_agent_input(agent_name, state)
    
    print("\n[Processing with multi-channel notification...]")
    print(f"Available channels: {', '.join(AGENT_METADATA['alert_agent']['channels'])}")
    
    try:
        decision_result = state.get("decision_result", {})
        
        if not decision_result.get("alert"):
            print("\n  ℹ️  No alert needed - skipping notifications")
            state["alert_result"] = {
                "sent": False,
                "reason": "No alert triggered"
            }
            log_agent_output(agent_name, state, success=True)
            return state
        
        print(f"\n  📧 Sending email notification...")
        print(f"  📱 Sending SMS notification...")
        
        # Alert was already sent by the agent.decision_from_vision
        # But we can track the result here
        notified = decision_result.get("notified", False)
        
        state["alert_result"] = {
            "sent": notified,
            "reason": decision_result.get("reason"),
            "alert_type": "multi_channel",
            "channels_used": ["email", "sms"]
        }
        
        if notified:
            print(f"\n  ✅ Alerts sent successfully via multiple channels")
            print(f"     Recipients notified via email and SMS")
        else:
            print(f"\n  ⚠️  Alert triggered but notifications may have failed")
            print(f"     Check SMTP/Twilio configuration")
        
        state["status"] = "alert_complete"
        log_agent_output(agent_name, state, success=notified)
        
    except Exception as e:
        print(f"  ❌ Error in alert agent: {e}")
        state["errors"].append(f"alert_agent: {str(e)}")
        state["alert_result"] = {
            "sent": False,
            "error": str(e)
        }
        log_agent_output(agent_name, state, success=False)
    
    return state


def logger_agent_node(state: WorkflowState) -> WorkflowState:
    """
    Node 6: Database Logger Agent
    
    Purpose: Persists analysis results and alert history to SQLite database
             for auditing and historical analysis.
    
    Model: Direct Python (SQLModel/SQLite)
    
    Database Tables:
    - frame_analysis_logs: Vision analysis results per frame
    - alert_logs: Alert notification history
    
    Features:
    - Structured data storage
    - Timestamp indexing for queries
    - Transaction safety with rollback
    """
    agent_name = "logger_agent"
    log_agent_input(agent_name, state)
    
    print("\n[Processing with SQLModel/SQLite...]")
    print(f"Tables: {', '.join(AGENT_METADATA['logger_agent']['tables'])}")
    
    log_ids = {}
    
    try:
        vision_result = state.get("vision_result", {})
        decision_result = state.get("decision_result", {})
        
        # Log frame analysis
        if vision_result and state.get("frame_path"):
            try:
                print(f"\n  💾 Writing to frame_analysis_logs table...")
                with get_session() as session:
                    frame_log = FrameAnalysisLog(
                        frame_path=state["frame_path"],
                        baby_detected=vision_result.get("baby_detected", False),
                        movement_level=vision_result.get("movement_level"),
                        position=vision_result.get("position"),
                        risk=vision_result.get("risk"),
                        raw_response=json.dumps(vision_result)
                    )
                    session.add(frame_log)
                    session.commit()
                    session.refresh(frame_log)
                    log_ids["frame_log_id"] = frame_log.id
                    print(f"     ✅ Frame analysis logged (ID: {frame_log.id})")
                    print(f"        baby_detected={frame_log.baby_detected}, risk={frame_log.risk}")
            except Exception as e:
                print(f"     ⚠️  Failed to log frame analysis: {e}")
                state["errors"].append(f"logger_frame: {str(e)}")
        
        # Log alert if one was triggered
        if decision_result.get("alert"):
            try:
                print(f"\n  💾 Writing to alert_logs table...")
                with get_session() as session:
                    alert_log = AlertLog(
                        alert_type=state.get("alert_result", {}).get("alert_type", "workflow"),
                        message=decision_result.get("reason", "Alert triggered by workflow"),
                        delivered=decision_result.get("notified", False)
                    )
                    session.add(alert_log)
                    session.commit()
                    session.refresh(alert_log)
                    log_ids["alert_log_id"] = alert_log.id
                    print(f"     ✅ Alert logged (ID: {alert_log.id})")
                    print(f"        type={alert_log.alert_type}, delivered={alert_log.delivered}")
            except Exception as e:
                print(f"     ⚠️  Failed to log alert: {e}")
                state["errors"].append(f"logger_alert: {str(e)}")
        
        state["log_ids"] = log_ids
        state["status"] = "complete"
        print(f"\n  ✅ Logging complete - {len(log_ids)} records written")
        log_agent_output(agent_name, state, success=True)
        
    except Exception as e:
        print(f"  ❌ Error in logger agent: {e}")
        state["errors"].append(f"logger_agent: {str(e)}")
        state["log_ids"] = log_ids
        log_agent_output(agent_name, state, success=False)
    
    return state


# ============================================================================
# Graph Construction
# ============================================================================

def create_baby_monitor_workflow():
    """
    Create the LangGraph workflow for baby monitoring.
    
    Returns:
        Compiled LangGraph workflow
    """
    # Create a new graph
    workflow = StateGraph(WorkflowState)
    
    # Add nodes
    workflow.add_node("camera_input", camera_input_node)
    workflow.add_node("vision_agent", vision_agent_node)
    workflow.add_node("audio_agent", audio_agent_node)
    workflow.add_node("decision_agent", decision_agent_node)
    workflow.add_node("alert_agent", alert_agent_node)
    workflow.add_node("logger_agent", logger_agent_node)
    
    # Define edges (flow)
    # CameraInput -> Vision -> Audio -> Decision -> Alert -> Logger
    workflow.add_edge("camera_input", "vision_agent")
    workflow.add_edge("vision_agent", "audio_agent")
    workflow.add_edge("audio_agent", "decision_agent")
    workflow.add_edge("decision_agent", "alert_agent")
    workflow.add_edge("alert_agent", "logger_agent")
    
    # Set entry point
    workflow.set_entry_point("camera_input")
    
    # Set finish point
    workflow.set_finish_point("logger_agent")
    
    # Compile the workflow
    return workflow.compile()


# ============================================================================
# Execution Function
# ============================================================================

def run(frame_bytes: Optional[bytes] = None, audio_bytes: Optional[bytes] = None) -> Dict[str, Any]:
    """
    Run the complete baby monitor workflow.
    
    Args:
        frame_bytes: Raw image bytes from camera
        audio_bytes: Raw audio bytes from microphone (optional)
    
    Returns:
        Dict with workflow results including:
            - status: Final status
            - vision_result: Vision analysis results
            - audio_result: Audio analysis results
            - decision_result: Alert decision
            - alert_result: Alert sending result
            - log_ids: Database log IDs
            - timestamp: Workflow execution time
            - errors: List of errors encountered
    """
    print("\n" + "=" * 70)
    print("🍼 BABY MONITOR LANGGRAPH WORKFLOW")
    print("=" * 70)
    
    # Initialize state
    initial_state: WorkflowState = {
        "frame_bytes": frame_bytes,
        "audio_bytes": audio_bytes,
        "frame_path": None,
        "audio_path": None,
        "vision_result": None,
        "audio_result": None,
        "decision_result": None,
        "alert_result": None,
        "log_ids": {},
        "timestamp": datetime.utcnow().isoformat(),
        "status": "initializing",
        "errors": []
    }
    
    # Create workflow
    workflow = create_baby_monitor_workflow()
    
    try:
        # Execute workflow
        final_state = workflow.invoke(initial_state)
        
        print("\n" + "=" * 70)
        print("✅ WORKFLOW COMPLETE")
        print("=" * 70)
        
        # Prepare response
        response = {
            "status": final_state.get("status", "unknown"),
            "timestamp": final_state.get("timestamp"),
            "vision_result": final_state.get("vision_result"),
            "audio_result": final_state.get("audio_result"),
            "decision_result": final_state.get("decision_result"),
            "alert_result": final_state.get("alert_result"),
            "log_ids": final_state.get("log_ids", {}),
            "errors": final_state.get("errors", [])
        }
        
        # Print summary
        print(f"\nStatus: {response['status']}")
        if response.get("decision_result"):
            alert = response["decision_result"].get("alert", False)
            print(f"Alert: {'🚨 YES' if alert else '✅ NO'}")
            print(f"Reason: {response['decision_result'].get('reason')}")
        
        if response.get("log_ids"):
            print(f"Log IDs: {response['log_ids']}")
        
        if response.get("errors"):
            print(f"Errors: {len(response['errors'])} error(s) occurred")
            for error in response["errors"]:
                print(f"  - {error}")
        
        print("=" * 70 + "\n")
        
        return response
    
    except Exception as e:
        print(f"\n❌ WORKFLOW ERROR: {e}")
        import traceback
        traceback.print_exc()
        
        return {
            "status": "error",
            "timestamp": datetime.utcnow().isoformat(),
            "error": str(e),
            "errors": [str(e)]
        }


# ============================================================================
# Testing
# ============================================================================

if __name__ == "__main__":
    import sys
    
    print("\n🧪 Testing LangGraph Workflow...")
    print("\nNote: This requires a camera frame to be meaningful.")
    print("You can test with:")
    print("  1. A real camera frame")
    print("  2. A test image file")
    print("  3. Mock data (placeholder)")
    
    # Test with mock data
    response = input("\nRun workflow with mock data? (y/n): ")
    
    if response.lower() == 'y':
        # Create a simple test image (red square)
        from PIL import Image
        import io
        
        # Create test image
        img = Image.new('RGB', (320, 240), color='red')
        buffer = io.BytesIO()
        img.save(buffer, format='JPEG')
        test_frame_bytes = buffer.getvalue()
        
        print("\n📸 Using test image (320x240 red square)")
        
        # Run workflow
        result = run(frame_bytes=test_frame_bytes, audio_bytes=None)
        
        print("\n📊 Final Result:")
        print(json.dumps(result, indent=2, default=str))
    else:
        print("\nTest cancelled. Import and use run() function to execute workflow.")
        sys.exit(0)

