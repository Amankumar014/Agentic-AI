# LangGraph Workflow Integration

This document explains the LangGraph workflow implementation for the baby monitor system.

## Overview

The `src/langgraph_workflow.py` file implements a complete analysis pipeline using LangGraph's state-based workflow system. It orchestrates 6 agents that process frames and make intelligent alert decisions.

## Workflow Architecture

```
┌─────────────────┐
│ CameraInputNode │ - Saves frame/audio bytes to temp files
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│  VisionAgent    │ - Analyzes frame with Azure OpenAI Vision
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│  AudioAgent     │ - Extracts features and classifies crying
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│ DecisionAgent   │ - Makes alert decision (rule-based fusion)
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│  AlertAgent     │ - Sends email/SMS notifications
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│  LoggerAgent    │ - Stores results in database
└─────────────────┘
```

## Node Functions

Each node is implemented as a function that:
1. Receives the workflow state
2. Calls real functions from existing modules
3. Updates the state with results
4. Returns the modified state

### Node 1: Camera Input
- **Function**: `camera_input_node()`
- **Calls**: `save_bytes_to_temp()` from `src.utils`
- **Purpose**: Save frame and audio bytes to temporary files

### Node 2: Vision Agent
- **Function**: `vision_agent_node()`
- **Calls**: `analyze_image_bytes()` from `src.azure_vision`
- **Purpose**: Analyze frame with Azure GPT-4 Vision

### Node 3: Audio Agent
- **Function**: `audio_agent_node()`
- **Calls**: 
  - `extract_librosa_features()` from `src.audio_agent_placeholder`
  - `classify_cry()` from `src.audio_agent_placeholder`
- **Purpose**: Extract audio features and detect crying

### Node 4: Decision Agent
- **Function**: `decision_agent_node()`
- **Calls**: `decision_from_vision()` from `src.agent`
- **Purpose**: Make alert decision using rule-based logic

### Node 5: Alert Agent
- **Function**: `alert_agent_node()`
- **Calls**: `send_alert()` from `src.notifier` (via decision agent)
- **Purpose**: Send email/SMS notifications

### Node 6: Logger Agent
- **Function**: `logger_agent_node()`
- **Calls**: Database operations via `src.models`
- **Purpose**: Store analysis and alert logs

## Usage

### Basic Usage

```python
from src.langgraph_workflow import run

# With frame only
with open('frame.jpg', 'rb') as f:
    frame_bytes = f.read()

result = run(frame_bytes=frame_bytes)

# With frame and audio
with open('frame.jpg', 'rb') as f:
    frame_bytes = f.read()
with open('audio.wav', 'rb') as f:
    audio_bytes = f.read()

result = run(frame_bytes=frame_bytes, audio_bytes=audio_bytes)
```

### Result Structure

```python
{
    "status": "complete",
    "timestamp": "2024-01-15T10:30:00",
    "vision_result": {
        "baby_detected": true,
        "risk": "safe",
        "movement_level": "low",
        "position": "lying on back",
        "notes": "Baby appears calm"
    },
    "audio_result": {
        "is_crying": false,
        "confidence": 0.15,
        "features": {...}
    },
    "decision_result": {
        "alert": false,
        "reason": "All parameters within normal range",
        "notified": false
    },
    "alert_result": {
        "sent": false,
        "reason": "No alert triggered"
    },
    "log_ids": {
        "frame_log_id": 123
    },
    "errors": []
}
```

## Integration with API

You can integrate the workflow into the API endpoint:

```python
# In src/api.py
from src.langgraph_workflow import run as run_workflow

@router.post("/frames/workflow/")
async def upload_frame_workflow(file: UploadFile = File(...)):
    """
    Process frame using LangGraph workflow.
    """
    # Read file
    image_bytes = await file.read()
    
    # Run workflow in thread pool
    result = await run_blocking(run_workflow, frame_bytes=image_bytes)
    
    return JSONResponse(content=result)
```

## Integration with Camera Loop

You can use the workflow in the camera loop:

```python
# In src/camera_loop.py
from src.langgraph_workflow import run as run_workflow

def stream_with_workflow(camera_index: int = 0):
    camera = cv2.VideoCapture(camera_index)
    
    while True:
        # Capture frame
        ret, frame = camera.read()
        success, buffer = cv2.imencode('.jpg', frame)
        frame_bytes = buffer.tobytes()
        
        # Run workflow
        result = run_workflow(frame_bytes=frame_bytes)
        
        # Check result
        if result.get("decision_result", {}).get("alert"):
            print(f"🚨 ALERT: {result['decision_result']['reason']}")
        
        time.sleep(5)
```

## State Management

The workflow uses a `WorkflowState` TypedDict that flows through all nodes:

```python
class WorkflowState(TypedDict):
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
```

## Error Handling

Each node has try-except blocks and logs errors to the `state["errors"]` list. The workflow continues even if individual nodes fail, allowing partial results.

## Testing

```bash
# Test the workflow
python src/langgraph_workflow.py

# It will prompt to run with mock data
# Or use programmatically:
```

```python
from src.langgraph_workflow import run
from PIL import Image
import io

# Create test image
img = Image.new('RGB', (320, 240), color='blue')
buffer = io.BytesIO()
img.save(buffer, format='JPEG')
test_bytes = buffer.getvalue()

# Run workflow
result = run(frame_bytes=test_bytes)
print(result)
```

## Advantages of LangGraph Approach

1. **Visual Flow**: Clear node-based architecture
2. **State Management**: Clean state passing between agents
3. **Modularity**: Each node is independent and testable
4. **Extensibility**: Easy to add new nodes or modify flow
5. **Debugging**: Each node logs its progress
6. **Reusability**: Nodes call existing functions, no duplication

## Future Enhancements

Potential improvements to the workflow:

1. **Conditional Edges**: Skip audio node if no audio bytes
2. **Parallel Execution**: Run vision and audio agents in parallel
3. **Retry Logic**: Retry failed nodes with backoff
4. **Caching**: Cache recent analysis results
5. **Streaming**: Support streaming video analysis
6. **Multi-Camera**: Process multiple camera feeds

## Performance Considerations

- Vision API calls take 2-5 seconds (network + processing)
- Audio feature extraction takes 1-2 seconds
- Database operations are fast (<100ms)
- Total workflow execution: 3-8 seconds typical

## Dependencies

The workflow requires:
- `langgraph` - Workflow orchestration
- All existing baby monitor modules
- Python 3.8+ for TypedDict support

