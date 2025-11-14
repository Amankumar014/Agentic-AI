"""
Decision agent for baby monitoring.
Implements rule-based fusion of vision and audio data to make alert decisions.
"""
from typing import Dict, Any, Optional, List

from src.config import get_settings
from src.notifier import send_alert, send_risk_alert
from src.alert_manager import get_alert_manager, AlertType


def decision_from_vision(
    vision_json: dict,
    audio_json: Optional[dict] = None
) -> dict:
    """
    Make an alert decision based on vision and audio analysis.
    Uses rule-based fusion to determine if an alert should be sent.
    
    Args:
        vision_json: Vision analysis results with keys like baby_detected, risk, movement_level, position, notes
        audio_json: Optional audio analysis results with keys like is_crying, confidence, etc.
    
    Returns:
        Dict with:
            - alert: bool (whether to send an alert)
            - reason: str (explanation of the decision)
            - vision: dict (original vision data)
            - audio: dict or None (original audio data)
            - notified: bool (whether notification was sent successfully)
    """
    settings = get_settings()
    
    alert = False
    reasons: List[str] = []
    
    # Extract vision data with safe defaults
    baby_detected = vision_json.get("baby_detected", False)
    risk = vision_json.get("risk", "").lower()
    movement_level = vision_json.get("movement_level", "").lower()
    position = vision_json.get("position", "unknown")
    notes = vision_json.get("notes", "")
    
    # Rule 1: High-risk situations (distress, fall, alert, caution, monitor)
    high_risk_keywords = ["distress", "fall", "alert", "danger", "caution", "monitor"]
    if any(keyword in risk for keyword in high_risk_keywords):
        alert = True
        reasons.append(f"Risk level: {risk}")
    
    # Rule 2: Baby not detected (possible fall or movement out of frame)
    if not baby_detected:
        alert = True
        reasons.append("Baby not detected in frame - possible fall or movement")
    
    # Rule 3: High movement level
    if movement_level == "high":
        alert = True
        reasons.append(f"High movement level detected: {movement_level}")
    
    # Rule 4: Moderate movement with caution/monitor risk
    if movement_level in ["moderate"] and risk in ["caution", "monitor"]:
        alert = True
        reasons.append(f"Moderate movement with {risk} risk level")
    
    # Rule 5: Crying or distress detected in vision notes
    # Check for positive distress indicators, not just keywords
    notes_lower = notes.lower()
    
    # Positive distress indicators
    distress_indicators = [
        "crying", "is crying", "appears to be crying", "seems to be crying",
        "tears", "tearful", "weeping",
        "fussing", "fussy", 
        "upset", "appears upset",
        "uncomfortable", "appears uncomfortable", "seems uncomfortable",
        "distressed", "appears distressed", "seems distressed", "showing distress",
        "mouth open wide", "mouth wide open", "open mouth crying"
    ]
    
    # Negative phrases that indicate NO distress (should NOT trigger)
    negative_phrases = [
        "no signs of distress", "no visible signs of distress",
        "no distress", "not distressed",
        "not crying", "no crying",
        "not uncomfortable", "no discomfort",
        "appears calm", "seems calm", "looks calm"
    ]
    
    # Check if any negative phrases are present
    has_negative = any(phrase in notes_lower for phrase in negative_phrases)
    
    # Only trigger if positive indicators are found AND no negative phrases
    if not has_negative:
        if any(indicator in notes_lower for indicator in distress_indicators):
            alert = True
            reasons.append(f"Baby appears distressed: {notes}")
    
    # Rule 6: Audio fusion - crying detected in audio
    if audio_json:
        is_crying = audio_json.get("is_crying", False)
        audio_confidence = audio_json.get("confidence", 0.0)
        
        if is_crying:
            # High confidence crying always alerts
            if audio_confidence > 0.7:
                alert = True
                reasons.append(f"Crying detected (confidence: {audio_confidence:.2f})")
            
            # Crying with suspicious movement or position
            elif movement_level in ["moderate", "high"] or risk in ["monitor", "caution", "alert"]:
                alert = True
                reasons.append(f"Crying detected with suspicious movement/position")
    
    # Rule 7: Specific position-based alerts
    dangerous_position_keywords = ["face down", "covered", "blanket", "obstruction", "unsafe"]
    if any(keyword in position.lower() for keyword in dangerous_position_keywords):
        alert = True
        reasons.append(f"Potentially unsafe position: {position}")
    
    if any(keyword in notes.lower() for keyword in dangerous_position_keywords):
        alert = True
        reasons.append(f"Safety concern in notes: {notes}")
    
    # Determine final reason
    if alert and reasons:
        reason = " | ".join(reasons)
    elif not alert:
        reason = "All parameters within normal range - no alert needed"
    else:
        reason = "Unknown alert trigger"
    
    # Send notification if alert is needed
    notified = False
    if alert:
        email_ok, sms_ok, log_id = send_alert_for_decision(
            vision_json=vision_json,
            audio_json=audio_json,
            reason=reason
        )
        notified = email_ok or sms_ok
    
    # Return decision
    return {
        "alert": alert,
        "reason": reason,
        "vision": vision_json,
        "audio": audio_json,
        "notified": notified
    }


def send_alert_for_decision(
    vision_json: dict,
    audio_json: Optional[dict],
    reason: str
) -> tuple:
    """
    Compose and send an alert based on analysis results.
    
    Includes cooldown logic to prevent alert spam. Alerts are only sent
    if the cooldown period has passed for the specific alert type.
    
    Args:
        vision_json: Vision analysis results
        audio_json: Optional audio analysis results
        reason: Reason for the alert
    
    Returns:
        Tuple of (email_success, sms_success, log_id)
    """
    from datetime import datetime
    
    # Extract key information
    baby_detected = vision_json.get("baby_detected", False)
    risk = vision_json.get("risk", "unknown")
    movement_level = vision_json.get("movement_level", "unknown")
    position = vision_json.get("position", "unknown")
    notes = vision_json.get("notes", "")
    
    # Determine alert type and emoji
    risk_lower = risk.lower()
    if risk_lower in ["alert", "danger"] or "fall" in risk_lower or "distress" in risk_lower:
        alert_type = "urgent_risk"
        cooldown_type = AlertType.HIGH_RISK
        emoji = "🚨"
    elif risk_lower == "caution":
        alert_type = "caution"
        cooldown_type = AlertType.BABY_DISTRESSED
        emoji = "⚠️"
    elif not baby_detected:
        alert_type = "baby_not_detected"
        cooldown_type = AlertType.BABY_ABSENT
        emoji = "❗"
    elif movement_level == "high":
        alert_type = "high_movement"
        cooldown_type = AlertType.HIGH_MOVEMENT
        emoji = "🏃"
    else:
        alert_type = "general"
        cooldown_type = AlertType.GENERAL
        emoji = "ℹ️"
    
    # Check cooldown before sending
    alert_manager = get_alert_manager()
    if not alert_manager.should_send_alert(cooldown_type):
        print(f"\n🔕 Alert skipped due to cooldown: {alert_type}")
        print(f"   Reason would have been: {reason}")
        status = alert_manager.get_cooldown_status(cooldown_type)
        remaining = status['cooldown_remaining_seconds']
        print(f"   Retry available in: {int(remaining/60)}m {int(remaining%60)}s")
        return False, False, None
    
    # Add audio context if available
    audio_context = ""
    if audio_json:
        is_crying = audio_json.get("is_crying", False)
        if is_crying:
            confidence = audio_json.get("confidence", 0.0)
            audio_context = f"\n🔊 Audio: Crying detected (confidence: {confidence:.0%})"
    
    # Compose message
    timestamp = datetime.now().strftime("%I:%M:%S %p")
    
    message = (
        f"{emoji} Baby Monitor Alert\n\n"
        f"Time: {timestamp}\n"
        f"Reason: {reason}\n\n"
        f"📹 Vision Analysis:\n"
        f"  • Baby Detected: {'Yes' if baby_detected else 'No'}\n"
        f"  • Risk Level: {risk.upper()}\n"
        f"  • Movement: {movement_level.upper()}\n"
        f"  • Position: {position}\n"
    )
    
    if notes:
        message += f"  • Notes: {notes}\n"
    
    if audio_context:
        message += audio_context + "\n"
    
    message += "\n⚠️ Please check the baby monitor immediately!"
    
    # Send alert
    print(f"\n📤 Sending alert: {alert_type} ({cooldown_type})")
    email_ok, sms_ok, log_id = send_alert(alert_type=alert_type, message=message)
    
    # Record successful alert for cooldown tracking
    if email_ok or sms_ok:
        alert_manager.record_alert_sent(cooldown_type)
        print(f"✅ Alert successfully sent and cooldown timer started")
    
    return email_ok, sms_ok, log_id


def evaluate_multiple_frames(
    frame_analyses: List[dict],
    audio_json: Optional[dict] = None
) -> dict:
    """
    Evaluate multiple consecutive frame analyses to reduce false positives.
    Uses temporal consistency to make more robust decisions.
    
    Args:
        frame_analyses: List of vision analysis results from consecutive frames
        audio_json: Optional audio analysis results
    
    Returns:
        Dict with aggregate decision
    """
    if not frame_analyses:
        return {
            "alert": False,
            "reason": "No frame data available",
            "vision": None,
            "audio": audio_json,
            "notified": False
        }
    
    # Use most recent frame as primary
    latest_frame = frame_analyses[-1]
    
    # Count concerning indicators across frames
    baby_not_detected_count = sum(1 for f in frame_analyses if not f.get("baby_detected", False))
    high_movement_count = sum(1 for f in frame_analyses if f.get("movement_level", "").lower() == "high")
    high_risk_count = sum(1 for f in frame_analyses if f.get("risk", "").lower() in ["alert", "caution", "danger"])
    
    # Temporal thresholds
    frame_count = len(frame_analyses)
    baby_missing_threshold = 0.5  # 50% of frames
    high_movement_threshold = 0.6  # 60% of frames
    high_risk_threshold = 0.4  # 40% of frames
    
    # Check if patterns persist across frames
    persistent_issue = (
        (baby_not_detected_count / frame_count) >= baby_missing_threshold or
        (high_movement_count / frame_count) >= high_movement_threshold or
        (high_risk_count / frame_count) >= high_risk_threshold
    )
    
    # If persistent issue or latest frame shows immediate danger, use decision logic
    if persistent_issue or latest_frame.get("risk", "").lower() in ["alert", "danger"]:
        return decision_from_vision(latest_frame, audio_json)
    else:
        return {
            "alert": False,
            "reason": "Transient anomaly - not persistent across frames",
            "vision": latest_frame,
            "audio": audio_json,
            "notified": False
        }


def is_safe_state(vision_json: dict, audio_json: Optional[dict] = None) -> bool:
    """
    Quick check if current state is safe (no immediate concerns).
    
    Args:
        vision_json: Vision analysis results
        audio_json: Optional audio analysis results
    
    Returns:
        bool: True if state is safe, False if concerns exist
    """
    baby_detected = vision_json.get("baby_detected", False)
    risk = vision_json.get("risk", "").lower()
    movement_level = vision_json.get("movement_level", "").lower()
    
    # Safe conditions
    safe_risk = risk in ["safe", "normal", "ok"]
    normal_movement = movement_level in ["none", "minimal", "low"]
    
    # Audio is calm
    audio_safe = True
    if audio_json:
        is_crying = audio_json.get("is_crying", False)
        audio_safe = not is_crying
    
    return baby_detected and safe_risk and normal_movement and audio_safe


if __name__ == "__main__":
    # Test the agent with sample data
    print("=" * 60)
    print("BABY MONITOR AGENT TEST")
    print("=" * 60)
    
    # Test case 1: Normal safe state
    print("\n[Test 1] Normal safe state:")
    vision_safe = {
        "baby_detected": True,
        "risk": "safe",
        "movement_level": "minimal",
        "position": "lying on back",
        "notes": "Baby appears calm"
    }
    result = decision_from_vision(vision_safe)
    print(f"  Alert: {result['alert']}")
    print(f"  Reason: {result['reason']}")
    
    # Test case 2: High movement
    print("\n[Test 2] High movement detected:")
    vision_movement = {
        "baby_detected": True,
        "risk": "monitor",
        "movement_level": "high",
        "position": "moving around",
        "notes": "Active movement"
    }
    result = decision_from_vision(vision_movement)
    print(f"  Alert: {result['alert']}")
    print(f"  Reason: {result['reason']}")
    
    # Test case 3: Baby not detected
    print("\n[Test 3] Baby not detected:")
    vision_missing = {
        "baby_detected": False,
        "risk": "alert",
        "movement_level": "none",
        "position": "not visible",
        "notes": "Baby not in frame"
    }
    result = decision_from_vision(vision_missing)
    print(f"  Alert: {result['alert']}")
    print(f"  Reason: {result['reason']}")
    
    # Test case 4: Crying with movement
    print("\n[Test 4] Crying with moderate movement:")
    vision_moderate = {
        "baby_detected": True,
        "risk": "monitor",
        "movement_level": "moderate",
        "position": "sitting up",
        "notes": "Baby seems distressed"
    }
    audio_crying = {
        "is_crying": True,
        "confidence": 0.85
    }
    result = decision_from_vision(vision_moderate, audio_crying)
    print(f"  Alert: {result['alert']}")
    print(f"  Reason: {result['reason']}")
    
    print("\n" + "=" * 60)
    print("Tests completed!")
    print("=" * 60)
