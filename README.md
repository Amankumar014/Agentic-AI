# Baby Monitor Backend System

AI-powered baby monitoring system with Azure OpenAI Vision, real-time frame analysis, and multi-channel alerting.

## 🎯 Features

- **Real-time Video Monitoring**: OpenCV camera capture with configurable intervals
- **Azure Vision AI**: GPT-4 Vision analysis for baby detection, movement tracking, and risk assessment
- **Audio Analysis**: Cry detection with librosa feature extraction (optional)
- **Rule-Based Agent**: Intelligent alert decision-making with vision + audio fusion
- **Multi-Channel Alerts**: Email (SMTP) and SMS (Twilio) notifications
- **RESTful API**: FastAPI endpoints for frame upload, logs, and alerts
- **Database Logging**: SQLModel/SQLite for analysis and alert history
- **Async Architecture**: Non-blocking async/await throughout

## 📁 Project Structure

```
baby_BE/
├── main.py                           # FastAPI application entrypoint
├── requirements.txt                  # Python dependencies
├── .env.example                      # Environment variables template
├── .gitignore                       # Git ignore rules
├── README.md                        # This file
├── AUDIO_INTEGRATION.md             # Audio integration guide
├── src/
│   ├── config.py                   # Configuration management (Pydantic)
│   ├── models.py                   # Database models (SQLModel)
│   ├── azure_vision.py             # Azure OpenAI Vision integration
│   ├── notifier.py                 # Email/SMS notification service
│   ├── agent.py                    # Decision agent (rule-based fusion)
│   ├── utils.py                    # Utility functions
│   ├── camera_loop.py              # Camera capture loop
│   ├── api.py                      # FastAPI router and endpoints
│   └── audio_agent_placeholder.py  # Audio recording and cry detection
├── temp/                            # Temporary files (frames, audio)
│   └── .gitkeep
└── models/                          # ML models directory
    ├── .gitkeep
    └── README.md                    # Model documentation
```

## 🚀 Quick Start

### 1. Installation

```bash
# Clone repository
cd baby_BE

# Create virtual environment
python -m venv .venv

# Activate virtual environment
# Windows:
.venv\Scripts\activate
# macOS/Linux:
source .venv/bin/activate

# Install dependencies
pip install -r requirements.txt
```

### 2. Configuration

```bash
# Copy environment template
cp .env.example .env

# Edit .env with your credentials
# Required: Azure OpenAI credentials
# Optional: SMTP and Twilio for alerts
```

### 3. Run Backend Server

```bash
# Start FastAPI server
python main.py
```

Server will start at `http://localhost:8000`
- Swagger UI: http://localhost:8000/docs
- ReDoc: http://localhost:8000/redoc

### 4. Run Camera Loop (separate terminal)

```bash
# Test camera
python src/camera_loop.py --test

# List available cameras
python src/camera_loop.py --list-cameras

# Start monitoring
python src/camera_loop.py --camera 0
```

## 🔑 Environment Variables

See `.env.example` for all available settings. Key variables:

**Azure OpenAI (Required for vision analysis):**
```env
AZURE_OPENAI_ENDPOINT=https://your-resource.openai.azure.com
AZURE_OPENAI_API_KEY=your-api-key
AZURE_OPENAI_DEPLOYMENT=gpt-4-vision
```

**Email Alerts (Optional):**
```env
SMTP_HOST=smtp.gmail.com
SMTP_PORT=587
SMTP_USER=your-email@gmail.com
SMTP_PASSWORD=your-app-password
ALERT_RECIPIENT_EMAIL=recipient@example.com
```

**SMS Alerts (Optional):**
```env
TWILIO_SID=your-twilio-sid
TWILIO_TOKEN=your-twilio-token
TWILIO_FROM=+1234567890
ALERT_RECIPIENT_PHONE=+1987654321
```

## 📡 API Endpoints

### POST `/api/v1/frames/`
Upload and analyze a baby monitor frame (image only) using **LangGraph workflow orchestration**
- **Input**: Multipart form-data with image file
- **Workflow**: Triggers LangGraph pipeline: CameraInput → Vision → Audio → Decision → Alert → Logger
- **Output**: Complete workflow results including analysis, decision, alerts, and log IDs

### POST `/api/v1/frames/with-audio/`
Upload and analyze a frame with audio using **LangGraph workflow orchestration**
- **Input**: Multipart form-data with image file AND audio file (both required)
- **Workflow**: Full pipeline with audio analysis included
- **Output**: Complete workflow results with audio cry detection

### GET `/api/v1/alerts/?limit=50`
Get recent alert logs

### GET `/api/v1/logs/?limit=50`
Get recent frame analysis logs

### GET `/api/v1/health/`
Health check endpoint

### GET `/api/v1/stats/`
System statistics (frames analyzed, alerts sent, etc.)

## 🎥 Camera Integration

```bash
# Basic usage
python src/camera_loop.py

# Custom camera and server
python src/camera_loop.py --camera 1 --server http://192.168.1.100:8000/api/v1/frames/

# Save frames locally
python src/camera_loop.py --save-local
```

## 🔊 Audio Integration (Optional)

Audio cry detection is available as an optional feature. See [AUDIO_INTEGRATION.md](AUDIO_INTEGRATION.md) for details.

```bash
# Install audio dependencies
pip install sounddevice librosa scipy

# Test audio system
python src/audio_agent_placeholder.py --test

# Record and analyze
python src/audio_agent_placeholder.py --record
```

## 🧠 How It Works

### Analysis Pipeline (LangGraph Orchestration)

The API uses **LangGraph workflow** to orchestrate the entire pipeline:

```
Camera → Upload to API → LangGraph Workflow
                              ↓
                    ┌─────────────────┐
                    │ CameraInputNode │ - Save frame/audio to temp
                    └────────┬────────┘
                             ↓
                    ┌─────────────────┐
                    │  VisionAgent    │ - Azure OpenAI Vision analysis
                    └────────┬────────┘
                             ↓
                    ┌─────────────────┐
                    │  AudioAgent     │ - Feature extraction & cry detection
                    └────────┬────────┘
                             ↓
                    ┌─────────────────┐
                    │ DecisionAgent   │ - Rule-based alert decision
                    └────────┬────────┘
                             ↓
                    ┌─────────────────┐
                    │  AlertAgent     │ - Send email/SMS notifications
                    └────────┬────────┘
                             ↓
                    ┌─────────────────┐
                    │  LoggerAgent    │ - Store in database
                    └─────────────────┘
```

See [LANGGRAPH_WORKFLOW.md](LANGGRAPH_WORKFLOW.md) for detailed workflow documentation.

### Alert Rules

The decision agent triggers alerts when:
1. **High Risk**: Risk level is "alert", "caution", "danger", or "distress"
2. **Baby Not Detected**: Possible fall or movement out of frame
3. **High Movement**: Sudden or sustained high movement level
4. **Audio + Movement**: Crying detected with suspicious movement
5. **Unsafe Position**: Face down, covered, or other dangerous positions

## 🗄️ Database

Uses SQLite by default (configurable via `DATABASE_URL`).

**Tables:**
- `frame_analysis_logs`: Vision analysis results for each frame
- `alert_logs`: History of all alerts sent

**View Data:**
```bash
# Using SQLite CLI
sqlite3 baby_monitor.db
> SELECT * FROM alert_logs ORDER BY timestamp DESC LIMIT 10;
```

## 🧪 Testing

```bash
# Test configuration
python -c "from src.config import get_settings; print(get_settings())"

# Test database
python -c "from src.models import init_db; init_db()"

# Test notifications
python src/notifier.py

# Test camera
python src/camera_loop.py --test

# Test audio
python src/audio_agent_placeholder.py --test
```

## 📊 Monitoring

View logs in real-time:
```bash
# Camera loop logs
python src/camera_loop.py

# API server logs
python main.py
```

Access metrics:
```bash
curl http://localhost:8000/api/v1/stats/
```

## 🔧 Troubleshooting

### Camera Not Found
```bash
# List available cameras
python src/camera_loop.py --list-cameras

# Try different indices
python src/camera_loop.py --camera 1
```

### Azure API Errors
- Check endpoint URL format (should include https://)
- Verify API key is correct
- Ensure deployment name matches your Azure setup
- Check Azure quota limits

### Email Not Sending
- For Gmail: Enable 2FA and create App Password
- Check SMTP port (587 for STARTTLS, 465 for SSL)
- Verify credentials

### SMS Not Sending
- Verify Twilio SID and Token
- Check phone number format (+1234567890)
- Ensure Twilio account has credits

## 🛡️ Security

- **Never commit `.env`** - Contains sensitive credentials
- **Use App Passwords** - For email services
- **API Keys** - Rotate regularly
- **CORS** - Configure for production (currently allows all origins)

## 📝 License

This is a personal project for baby monitoring. Use at your own risk.

## 🤝 Contributing

This is a personal project, but feel free to fork and adapt for your needs!

## 📧 Support

For issues or questions, check:
1. Logs in console output
2. Database entries (`baby_monitor.db`)
3. Configuration in `.env`
4. API docs at `/docs`

