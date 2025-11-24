"""
Alert Manager - Cooldown System for Baby Monitor Notifications

This module prevents alert spam by implementing a configurable cooldown period
for different alert types. Ensures alerts are only sent once per cooldown period,
avoiding notification fatigue for parents while maintaining safety.

Features:
- Thread-safe alert tracking using threading.Lock
- Per-alert-type cooldown tracking
- Configurable cooldown periods
- Clear logging for sent/skipped alerts
- Production-ready with proper error handling
"""
import threading
import sys
from datetime import datetime, timedelta
from typing import Dict, Optional
from enum import Enum


def safe_print(message: str) -> None:
    """
    Safely print message with emoji support.
    Falls back to ASCII if terminal doesn't support Unicode.
    """
    try:
        print(message)
    except UnicodeEncodeError:
        # Replace common emojis with ASCII equivalents
        ascii_message = (message
            .replace("🔔", "[ALERT]")
            .replace("⏳", "[WAIT]")
            .replace("✅", "[OK]")
            .replace("🔄", "[RESET]")
            .replace("🚨", "[!!!]")
            .replace("📤", "[SEND]")
            .replace("🔕", "[SKIP]")
            .replace("🎉", "[SUCCESS]")
            .replace("⚠️", "[WARN]")
            .replace("❌", "[FAIL]"))
        try:
            print(ascii_message)
        except UnicodeEncodeError:
            # If still failing, strip all non-ASCII characters
            print(ascii_message.encode('ascii', 'ignore').decode('ascii'))


class AlertType(str, Enum):
    """
    Enumeration of alert types tracked by the system.
    Each type can have independent cooldown tracking.
    """
    BABY_ABSENT = "baby_absent"
    BABY_DISTRESSED = "baby_distressed"
    HIGH_MOVEMENT = "high_movement"
    UNSAFE_POSITION = "unsafe_position"
    CRYING_DETECTED = "crying_detected"
    HIGH_RISK = "high_risk"
    GENERAL = "general"


class AlertManager:
    """
    Thread-safe alert cooldown manager.
    
    Tracks the last alert timestamp for each alert type and enforces
    a configurable cooldown period to prevent alert spam.
    
    Usage:
        manager = AlertManager(cooldown_minutes=5)
        
        if manager.should_send_alert(AlertType.BABY_ABSENT):
            send_notification()
            manager.record_alert_sent(AlertType.BABY_ABSENT)
    
    Attributes:
        cooldown_seconds: Cooldown period in seconds
        _last_alert_times: Dict tracking last alert timestamp per type
        _lock: Threading lock for thread-safe operations
    """
    
    def __init__(self, cooldown_minutes: int = 5):
        """
        Initialize the AlertManager with a cooldown period.
        
        Args:
            cooldown_minutes: Minutes to wait between alerts of the same type (default: 5)
        """
        self.cooldown_seconds = cooldown_minutes * 60
        self._last_alert_times: Dict[str, datetime] = {}
        self._lock = threading.Lock()
        
        safe_print(f"🔔 AlertManager initialized (cooldown: {cooldown_minutes} minutes)")
    
    def should_send_alert(self, alert_type: str) -> bool:
        """
        Check if an alert should be sent based on cooldown period.
        
        Thread-safe method that determines if enough time has passed since
        the last alert of this type was sent.
        
        Args:
            alert_type: Type of alert (e.g., "baby_absent", "baby_distressed")
        
        Returns:
            bool: True if alert should be sent, False if in cooldown period
        """
        with self._lock:
            # Normalize alert type
            alert_type = str(alert_type).lower()
            
            # Check if this alert type has been sent before
            if alert_type not in self._last_alert_times:
                return True
            
            # Calculate time since last alert
            last_alert_time = self._last_alert_times[alert_type]
            time_since_last = datetime.now() - last_alert_time
            cooldown_remaining = self.cooldown_seconds - time_since_last.total_seconds()
            
            # Check if cooldown period has passed
            if time_since_last.total_seconds() >= self.cooldown_seconds:
                return True
            else:
                # Still in cooldown
                minutes_remaining = int(cooldown_remaining / 60)
                seconds_remaining = int(cooldown_remaining % 60)
                safe_print(f"⏳ Alert '{alert_type}' in cooldown (wait {minutes_remaining}m {seconds_remaining}s)")
                return False
    
    def record_alert_sent(self, alert_type: str) -> None:
        """
        Record that an alert was sent successfully.
        
        Updates the last alert timestamp for the given alert type.
        Call this immediately after successfully sending an alert.
        
        Args:
            alert_type: Type of alert that was sent
        """
        with self._lock:
            alert_type = str(alert_type).lower()
            self._last_alert_times[alert_type] = datetime.now()
            safe_print(f"✅ Alert sent and recorded: '{alert_type}' at {datetime.now().strftime('%H:%M:%S')}")
    
    def reset_cooldown(self, alert_type: str) -> None:
        """
        Reset the cooldown for a specific alert type.
        
        Useful for testing or manual override situations.
        
        Args:
            alert_type: Type of alert to reset
        """
        with self._lock:
            alert_type = str(alert_type).lower()
            if alert_type in self._last_alert_times:
                del self._last_alert_times[alert_type]
                safe_print(f"🔄 Cooldown reset for alert type: '{alert_type}'")
    
    def reset_all_cooldowns(self) -> None:
        """
        Reset all cooldowns.
        
        Clears all tracked alert timestamps. Useful for testing or emergency situations.
        """
        with self._lock:
            self._last_alert_times.clear()
            safe_print("🔄 All alert cooldowns reset")
    
    def get_cooldown_status(self, alert_type: str) -> Dict[str, any]:
        """
        Get the current cooldown status for an alert type.
        
        Args:
            alert_type: Type of alert to check
        
        Returns:
            Dict with keys:
                - can_send: bool (whether alert can be sent now)
                - last_sent: datetime or None (when last alert was sent)
                - cooldown_remaining_seconds: float (seconds until can send again)
        """
        with self._lock:
            alert_type = str(alert_type).lower()
            
            if alert_type not in self._last_alert_times:
                return {
                    "can_send": True,
                    "last_sent": None,
                    "cooldown_remaining_seconds": 0
                }
            
            last_sent = self._last_alert_times[alert_type]
            time_since_last = datetime.now() - last_sent
            cooldown_remaining = max(0, self.cooldown_seconds - time_since_last.total_seconds())
            
            return {
                "can_send": cooldown_remaining == 0,
                "last_sent": last_sent,
                "cooldown_remaining_seconds": cooldown_remaining
            }
    
    def get_all_status(self) -> Dict[str, Dict]:
        """
        Get cooldown status for all tracked alert types.
        
        Returns:
            Dict mapping alert_type -> status dict
        """
        with self._lock:
            return {
                alert_type: self.get_cooldown_status(alert_type)
                for alert_type in self._last_alert_times.keys()
            }


# Global singleton instance
_alert_manager: Optional[AlertManager] = None
_manager_lock = threading.Lock()


def get_alert_manager(cooldown_minutes: Optional[int] = None) -> AlertManager:
    """
    Get the global AlertManager singleton instance.
    
    Lazy initialization pattern ensures only one manager exists.
    Thread-safe initialization.
    
    Args:
        cooldown_minutes: Optional cooldown period in minutes.
                         Only used on first initialization.
    
    Returns:
        AlertManager: Global alert manager instance
    """
    global _alert_manager
    
    with _manager_lock:
        if _alert_manager is None:
            # Get cooldown from config if not provided
            if cooldown_minutes is None:
                try:
                    from src.config import get_settings
                    settings = get_settings()
                    cooldown_minutes = getattr(settings, 'ALERT_COOLDOWN_MINUTES', 5)
                except Exception:
                    cooldown_minutes = 5  # Default fallback
            
            _alert_manager = AlertManager(cooldown_minutes=cooldown_minutes)
        
        return _alert_manager


def reset_alert_manager() -> None:
    """
    Reset the global AlertManager instance.
    
    Useful for testing or when configuration changes.
    """
    global _alert_manager
    
    with _manager_lock:
        _alert_manager = None


# ============================================================================
# Testing and Examples
# ============================================================================

if __name__ == "__main__":
    import time
    
    print("=" * 70)
    print("ALERT MANAGER TEST")
    print("=" * 70)
    
    # Create manager with 30 second cooldown for testing
    manager = AlertManager(cooldown_minutes=0.5)  # 30 seconds
    
    # Test 1: First alert should go through
    print("\n[Test 1] First alert - should send")
    alert_type = AlertType.BABY_ABSENT
    if manager.should_send_alert(alert_type):
        print(f"✅ Sending alert: {alert_type}")
        manager.record_alert_sent(alert_type)
    else:
        print(f"❌ Alert blocked: {alert_type}")
    
    # Test 2: Immediate second alert should be blocked
    print("\n[Test 2] Immediate second alert - should be blocked")
    if manager.should_send_alert(alert_type):
        print(f"✅ Sending alert: {alert_type}")
        manager.record_alert_sent(alert_type)
    else:
        print(f"⏳ Alert blocked by cooldown: {alert_type}")
    
    # Test 3: Different alert type should go through
    print("\n[Test 3] Different alert type - should send")
    alert_type_2 = AlertType.CRYING_DETECTED
    if manager.should_send_alert(alert_type_2):
        print(f"✅ Sending alert: {alert_type_2}")
        manager.record_alert_sent(alert_type_2)
    else:
        print(f"❌ Alert blocked: {alert_type_2}")
    
    # Test 4: Check status
    print("\n[Test 4] Cooldown status check")
    status = manager.get_cooldown_status(alert_type)
    print(f"Alert type: {alert_type}")
    print(f"  Can send: {status['can_send']}")
    print(f"  Last sent: {status['last_sent']}")
    print(f"  Cooldown remaining: {status['cooldown_remaining_seconds']:.1f}s")
    
    # Test 5: Wait and try again
    print("\n[Test 5] Waiting 5 seconds and retrying...")
    time.sleep(5)
    if manager.should_send_alert(alert_type):
        print(f"✅ Sending alert: {alert_type}")
        manager.record_alert_sent(alert_type)
    else:
        print(f"⏳ Alert still blocked: {alert_type}")
    
    # Test 6: Reset cooldown
    print("\n[Test 6] Reset cooldown and retry")
    manager.reset_cooldown(alert_type)
    if manager.should_send_alert(alert_type):
        print(f"✅ Sending alert: {alert_type}")
        manager.record_alert_sent(alert_type)
    else:
        print(f"❌ Alert blocked: {alert_type}")
    
    # Test 7: Get all status
    print("\n[Test 7] All cooldown statuses")
    all_status = manager.get_all_status()
    for alert_type, status in all_status.items():
        print(f"\n{alert_type}:")
        print(f"  Can send: {status['can_send']}")
        print(f"  Cooldown remaining: {status['cooldown_remaining_seconds']:.1f}s")
    
    print("\n" + "=" * 70)
    print("TEST COMPLETE")
    print("=" * 70)

