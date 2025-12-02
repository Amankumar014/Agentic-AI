"""
Configuration management for the application.
Loads environment variables and provides centralized settings access.
"""
import os
from pathlib import Path
from typing import Optional

try:
    from pydantic_settings import BaseSettings, SettingsConfigDict
except ImportError:
    # Fallback for older pydantic versions
    from pydantic import BaseSettings
    SettingsConfigDict = None


class Settings(BaseSettings):
    """
    Application settings loaded from environment variables.
    Uses .env file if present in the project root.
    """
    
    # Azure OpenAI Configuration (for baby monitoring)
    AZURE_OPENAI_ENDPOINT: str = ""
    AZURE_OPENAI_API_KEY: str = ""
    AZURE_OPENAI_DEPLOYMENT: str = ""
    
    # Azure OpenAI Configuration (for chatbot specifically)
    CHATBOT_AZURE_OPENAI_ENDPOINT: str = ""
    CHATBOT_AZURE_OPENAI_API_KEY: str = ""
    CHATBOT_AZURE_OPENAI_DEPLOYMENT: str = ""
    
    # HuggingFace Configuration (for chatbot)
    HF_TOKEN: str = ""
    
    # SMTP Email Configuration
    SMTP_HOST: str = ""
    SMTP_PORT: int = 587
    SMTP_USER: str = ""
    SMTP_PASSWORD: str = ""
    
    # Twilio SMS Configuration
    TWILIO_SID: str = ""
    TWILIO_TOKEN: str = ""
    TWILIO_FROM: str = ""
    
    # Alert Recipients
    ALERT_RECIPIENT_EMAIL: str = ""
    ALERT_RECIPIENT_PHONE: str = ""
    
    # Database Configuration
    DATABASE_URL: str = "sqlite:///./baby_monitor.db"
    
    # Frame Analysis Settings
    FRAME_ANALYZE_INTERVAL: int = 5  # seconds between frame analyses
    
    # Audio Settings
    AUDIO_SAMPLE_RATE: int = 16000  # Hz
    AUDIO_DURATION: int = 3  # seconds
    
    # Alert Cooldown Settings
    ALERT_COOLDOWN_MINUTES: int = 5  # minutes between alerts of same type
    
    # Computer Vision / ML Models
    YOLO_MODEL_PATH: str = "yolov8n.pt"
    EMOTION_MODEL_PATH: str = "ml_models/best_model.h5"
    
    # Face Mesh and Iris Tracking Settings
    ENABLE_FACE_MESH: bool = True  # Enable MediaPipe Face Mesh detection
    ENABLE_IRIS_TRACKING: bool = True  # Enable MediaPipe Iris tracking
    
    # Pose Estimation Settings
    ENABLE_POSE_ESTIMATION: bool = True  # Enable MediaPipe Pose estimation
    
    # Emotion Detection Settings
    ENABLE_EMOTION_DETECTION: bool = True  # Enable emotion detection model
    
    # Annotated Video Visualization Settings
    ANNOTATED_STREAM_DRAW_BBOXES: bool = True  # Draw bounding boxes
    ANNOTATED_STREAM_DRAW_POSE: bool = True  # Draw pose skeleton
    ANNOTATED_STREAM_DRAW_FACE_MESH: bool = True  # Draw face mesh
    ANNOTATED_STREAM_DRAW_IRIS: bool = True  # Draw iris tracking
    ANNOTATED_STREAM_DRAW_LABELS: bool = True  # Draw text labels
    ANNOTATED_STREAM_DRAW_STATUS: bool = True  # Draw status overlay
    
    # Movement Tracking Thresholds
    MOVEMENT_STILL_THRESHOLD: float = 0.35
    MOVEMENT_MICRO_THRESHOLD: float = 0.85
    MOVEMENT_MAJOR_THRESHOLD: float = 2.0
    MOVEMENT_JERK_DELTA: float = 1.2
    MOVEMENT_STILLNESS_ALERT_SECONDS: int = 60
    
    # Camera Streaming Settings
    CAMERA_INDEX: int = 0  # Default camera device index
    STREAM_FPS: int = 15  # Frames per second for streaming
    STREAM_JPEG_QUALITY: int = 85  # JPEG quality (1-100, higher = better quality but larger size)
    STREAM_MAX_WIDTH: int = 1280  # Maximum width for streaming (0 = no limit) 1280 default
    STREAM_MAX_HEIGHT: int = 720 # Maximum height for streaming (0 = no limit) 720 default
    
    if SettingsConfigDict is not None:
        model_config = SettingsConfigDict(
            env_file=".env",
            env_file_encoding="utf-8",
            case_sensitive=True,
            extra="ignore"
        )
    else:
        class Config:
            env_file = ".env"
            env_file_encoding = "utf-8"
            case_sensitive = True
            extra = "ignore"


def ensure_directories() -> None:
    """
    Ensure required directories exist.
    Creates temp/ directory if it doesn't exist.
    """
    # Get project root (parent of src/)
    project_root = Path(__file__).parent.parent
    
    # Directories to ensure exist
    directories = [
        project_root / "temp",
    ]
    
    for directory in directories:
        directory.mkdir(parents=True, exist_ok=True)


# Global settings instance
_settings: Optional[Settings] = None


def get_settings() -> Settings:
    """
    Get the global settings instance.
    Lazy initialization pattern for import safety.
    
    Returns:
        Settings: The application settings instance
    """
    global _settings
    if _settings is None:
        _settings = Settings()
        ensure_directories()
    return _settings


# Convenience function for direct access
def reload_settings() -> Settings:
    """
    Force reload settings from environment.
    Useful for testing or dynamic configuration changes.
    
    Returns:
        Settings: Fresh settings instance
    """
    global _settings
    _settings = Settings()
    ensure_directories()
    return _settings


if __name__ == "__main__":
    # Test configuration loading
    settings = get_settings()
    print("Configuration loaded successfully!")
    print(f"Azure Endpoint: {settings.AZURE_OPENAI_ENDPOINT or '(not set)'}")
    print(f"Database URL: {settings.DATABASE_URL}")
    print(f"Frame Interval: {settings.FRAME_ANALYZE_INTERVAL}s")
    print(f"Audio Rate: {settings.AUDIO_SAMPLE_RATE}Hz")
    print(f"Audio Duration: {settings.AUDIO_DURATION}s")
    print(f"Temp directory: {Path(__file__).parent.parent / 'temp'}")
