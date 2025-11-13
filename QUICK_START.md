# Quick Start Guide

Get the baby monitor backend running in 5 minutes.

## Prerequisites

- Python 3.8+
- Webcam/camera
- Azure OpenAI account (for vision analysis)

## Installation

```bash
# 1. Navigate to project directory
cd baby_BE

# 2. Create virtual environment
python -m venv .venv

# 3. Activate virtual environment
# Windows:
.venv\Scripts\activate
# macOS/Linux:
source .venv/bin/activate

# 4. Install dependencies
pip install -r requirements.txt
```

## Configuration

```bash
# 1. Copy environment template
cp .env.example .env

# 2. Edit .env with your credentials
# Required for basic functionality:
AZURE_OPENAI_ENDPOINT=https://your-resource.openai.azure.com
AZURE_OPENAI_API_KEY=your-api-key-here
AZURE_OPENAI_DEPLOYMENT=gpt-4-vision

# Optional (for alerts):
SMTP_HOST=smtp.gmail.com
SMTP_PORT=587
SMTP_USER=your-email@gmail.com
SMTP_PASSWORD=your-app-password
ALERT_RECIPIENT_EMAIL=recipient@example.com
```

## Running

### Start the Backend Server

```bash
python main.py
```

Server will start at: `http://localhost:8000`
- API docs: http://localhost:8000/docs
- Alternative docs: http://localhost:8000/redoc

### Start Camera Monitoring (in another terminal)

```bash
# Test camera first
python src/camera_loop.py --test

# Start monitoring
python src/camera_loop.py --camera 0
```

## Testing the API

### Option 1: Using Browser
Visit http://localhost:8000/docs and use the interactive API interface.

### Option 2: Using curl

**Upload an image:**
```bash
curl -X POST http://localhost:8000/api/v1/frames/ \
  -F "file=@/path/to/image.jpg"
```

**Upload image + audio:**
```bash
curl -X POST http://localhost:8000/api/v1/frames/with-audio/ \
  -F "file=@/path/to/image.jpg" \
  -F "audio=@/path/to/audio.wav"
```

**Check health:**
```bash
curl http://localhost:8000/api/v1/health/
```

**View recent logs:**
```bash
curl http://localhost:8000/api/v1/logs/?limit=5
```

### Option 3: Using Test Script

```bash
python test_workflow_api.py
```

## Expected Workflow

When you upload an image, you'll see:

```
🚀 Triggering LangGraph workflow for frame analysis...

======================================================================
🔵 INPUT → Camera Input Agent
======================================================================
Purpose: Receives and validates raw camera frame and audio data...
[Processing...]
  ✅ Frame saved: temp/frame_20240115_103000_abc123.jpg

======================================================================
🔵 INPUT → Vision Analysis Agent
======================================================================
Purpose: Analyzes video frames using Azure OpenAI GPT-4 Vision...
[Processing with Azure OpenAI Vision...]
  ✅ Vision analysis complete
     Baby detected: True
     Risk: safe, Movement: low

[... continues through all 6 agents ...]

✅ WORKFLOW COMPLETE
```

## API Response Example

```json
{
  "status": "complete",
  "timestamp": "2024-01-15T10:30:00.000Z",
  "analysis": {
    "baby_detected": true,
    "risk": "safe",
    "movement_level": "low",
    "position": "lying on back",
    "notes": "Baby appears calm"
  },
  "decision": {
    "alert": false,
    "reason": "All parameters within normal range"
  },
  "alert": false,
  "log_ids": {
    "frame_log_id": 1
  }
}
```

## Common Issues

### 422 Error when uploading image

**Problem:** Using wrong endpoint or sending unexpected data.

**Solution:** Use the correct endpoint:
- Image only: `/api/v1/frames/`
- Image + audio: `/api/v1/frames/with-audio/`

### Azure API Error

**Problem:** Invalid credentials or configuration.

**Solution:** 
1. Check `.env` file
2. Verify Azure deployment is active
3. Ensure API key is valid

### Camera not found

**Problem:** Wrong camera index.

**Solution:**
```bash
# List cameras
python src/camera_loop.py --list-cameras

# Try different index
python src/camera_loop.py --camera 1
```

## Next Steps

1. **Test notifications:**
```bash
python src/notifier.py
```

2. **Test audio (optional):**
```bash
python src/audio_agent_placeholder.py --test
```

3. **View database:**
```bash
sqlite3 baby_monitor.db
> SELECT * FROM frame_analysis_logs ORDER BY timestamp DESC LIMIT 5;
```

4. **Check statistics:**
```bash
curl http://localhost:8000/api/v1/stats/
```

## Full Documentation

- [README.md](README.md) - Complete system documentation
- [LANGGRAPH_WORKFLOW.md](LANGGRAPH_WORKFLOW.md) - Workflow details
- [TROUBLESHOOTING.md](TROUBLESHOOTING.md) - Common issues and solutions
- [AUDIO_INTEGRATION.md](AUDIO_INTEGRATION.md) - Audio setup guide

## Getting Help

If something doesn't work:

1. Check the [TROUBLESHOOTING.md](TROUBLESHOOTING.md) guide
2. Review console logs for errors
3. Test individual components:
   - Config: `python -c "from src.config import get_settings; print(get_settings())"`
   - Database: `python -c "from src.models import init_db; init_db()"`
   - Camera: `python src/camera_loop.py --test`

## Stopping the System

```bash
# Stop server: Ctrl+C in the terminal
# Stop camera loop: Ctrl+C in the terminal
# Deactivate venv: deactivate
```

---

**You're ready to monitor!** 🍼👶📹

