"""
Database models and session management.
Defines SQLModel tables and provides database utilities.
"""
from datetime import datetime
from typing import Optional, Generator
from contextlib import contextmanager

from sqlmodel import Field, SQLModel, Session, create_engine
from sqlalchemy.engine import Engine


# ============================================================================
# Models
# ============================================================================

class FrameAnalysisLog(SQLModel, table=True):
    """
    Log of frame analysis results from vision AI.
    Stores analysis metadata and results for each frame processed.
    """
    __tablename__ = "frame_analysis_logs"
    
    id: Optional[int] = Field(default=None, primary_key=True)
    timestamp: datetime = Field(default_factory=datetime.utcnow, index=True)
    frame_path: str = Field(description="Path to the analyzed frame image")
    baby_detected: bool = Field(default=False, description="Whether baby was detected")
    movement_level: Optional[str] = Field(default=None, description="Movement level (e.g., low, medium, high)")
    position: Optional[str] = Field(default=None, description="Baby's position description")
    risk: Optional[str] = Field(default=None, description="Risk assessment (e.g., safe, caution, alert)")
    raw_response: Optional[str] = Field(default=None, description="Raw JSON response from AI")


class AlertLog(SQLModel, table=True):
    """
    Log of alerts sent to recipients.
    Tracks all notifications sent via email/SMS.
    """
    __tablename__ = "alert_logs"
    
    id: Optional[int] = Field(default=None, primary_key=True)
    timestamp: datetime = Field(default_factory=datetime.utcnow, index=True)
    alert_type: str = Field(description="Type of alert (e.g., movement, sound, risk)")
    message: str = Field(description="Alert message content")
    delivered: bool = Field(default=False, description="Whether alert was successfully delivered")


# ============================================================================
# Database Management
# ============================================================================

# Global engine instance
_engine: Optional[Engine] = None


def get_engine() -> Engine:
    """
    Get or create the database engine.
    Lazy initialization for import safety.
    
    Returns:
        Engine: SQLAlchemy engine instance
    """
    global _engine
    if _engine is None:
        from src.config import get_settings
        settings = get_settings()
        
        # Create engine with appropriate settings
        connect_args = {}
        if settings.DATABASE_URL.startswith("sqlite"):
            # SQLite specific settings
            connect_args = {"check_same_thread": False}
        
        _engine = create_engine(
            settings.DATABASE_URL,
            echo=False,  # Set to True for SQL query debugging
            connect_args=connect_args
        )
    
    return _engine


def init_db() -> None:
    """
    Initialize the database.
    Creates all tables defined in SQLModel metadata.
    Safe to call multiple times - only creates tables if they don't exist.
    """
    engine = get_engine()
    SQLModel.metadata.create_all(engine)
    print(f"Database initialized at: {engine.url}")


@contextmanager
def get_session() -> Generator[Session, None, None]:
    """
    Context manager for database sessions.
    Automatically handles commit/rollback and session cleanup.
    
    Usage:
        with get_session() as session:
            frame_log = FrameAnalysisLog(frame_path="path/to/frame.jpg")
            session.add(frame_log)
            session.commit()
    
    Yields:
        Session: SQLModel database session
    """
    engine = get_engine()
    session = Session(engine)
    try:
        yield session
        session.commit()
    except Exception as e:
        session.rollback()
        raise e
    finally:
        session.close()


def get_session_direct() -> Session:
    """
    Get a database session directly (non-context manager).
    Caller is responsible for closing the session.
    
    Returns:
        Session: SQLModel database session
    """
    engine = get_engine()
    return Session(engine)


# ============================================================================
# Helper Functions
# ============================================================================

def create_frame_log(
    frame_path: str,
    baby_detected: bool = False,
    movement_level: Optional[str] = None,
    position: Optional[str] = None,
    risk: Optional[str] = None,
    raw_response: Optional[str] = None
) -> FrameAnalysisLog:
    """
    Create and persist a frame analysis log entry.
    
    Args:
        frame_path: Path to the analyzed frame
        baby_detected: Whether baby was detected
        movement_level: Movement level description
        position: Position description
        risk: Risk assessment
        raw_response: Raw AI response
    
    Returns:
        FrameAnalysisLog: The created log entry
    """
    with get_session() as session:
        log = FrameAnalysisLog(
            frame_path=frame_path,
            baby_detected=baby_detected,
            movement_level=movement_level,
            position=position,
            risk=risk,
            raw_response=raw_response
        )
        session.add(log)
        session.commit()
        session.refresh(log)
        return log


def create_alert_log(
    alert_type: str,
    message: str,
    delivered: bool = False
) -> AlertLog:
    """
    Create and persist an alert log entry.
    
    Args:
        alert_type: Type of alert
        message: Alert message
        delivered: Whether alert was delivered
    
    Returns:
        AlertLog: The created log entry
    """
    with get_session() as session:
        log = AlertLog(
            alert_type=alert_type,
            message=message,
            delivered=delivered
        )
        session.add(log)
        session.commit()
        session.refresh(log)
        return log


if __name__ == "__main__":
    # Test database setup
    print("Initializing database...")
    init_db()
    
    # Test creating a frame log
    print("\nCreating test frame analysis log...")
    frame_log = create_frame_log(
        frame_path="temp/test_frame.jpg",
        baby_detected=True,
        movement_level="low",
        position="center",
        risk="safe",
        raw_response='{"status": "ok"}'
    )
    print(f"Created frame log ID: {frame_log.id}")
    
    # Test creating an alert log
    print("\nCreating test alert log...")
    alert_log = create_alert_log(
        alert_type="test",
        message="Test alert message",
        delivered=True
    )
    print(f"Created alert log ID: {alert_log.id}")
    
    print("\n✅ Database models tested successfully!")
