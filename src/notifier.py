"""
Notification service for sending alerts via email and SMS.
Handles email (SMTP) and SMS (Twilio) notifications with logging.
Includes cooldown management to prevent alert spam.
"""
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from typing import Optional, Tuple

from src.config import get_settings
from src.models import get_session, AlertLog
from src.alert_manager import get_alert_manager, AlertType


def send_email(subject: str, body: str) -> bool:
    """
    Send an email notification using SMTP.
    
    Args:
        subject: Email subject line
        body: Email body content
    
    Returns:
        bool: True if email sent successfully, False otherwise
    """
    settings = get_settings()
    
    # Validate SMTP configuration
    if not settings.SMTP_HOST or not settings.SMTP_USER or not settings.SMTP_PASSWORD:
        print("⚠️  SMTP not configured - skipping email notification")
        return False
    
    if not settings.ALERT_RECIPIENT_EMAIL:
        print("⚠️  No recipient email configured - skipping email notification")
        return False
    
    try:
        # Create message
        message = MIMEMultipart("alternative")
        message["Subject"] = subject
        message["From"] = settings.SMTP_USER
        message["To"] = settings.ALERT_RECIPIENT_EMAIL
        
        # Add body as plain text
        text_part = MIMEText(body, "plain")
        message.attach(text_part)
        
        # Connect to SMTP server and send
        # Using STARTTLS for secure connection
        with smtplib.SMTP(settings.SMTP_HOST, settings.SMTP_PORT) as server:
            server.ehlo()  # Identify ourselves to the server
            
            # Start TLS encryption
            if settings.SMTP_PORT != 465:  # 465 is SSL, others use STARTTLS
                server.starttls()
                server.ehlo()  # Re-identify after STARTTLS
            
            # Login and send
            server.login(settings.SMTP_USER, settings.SMTP_PASSWORD)
            server.send_message(message)
        
        print(f"✅ Email sent to {settings.ALERT_RECIPIENT_EMAIL}")
        return True
    
    except smtplib.SMTPAuthenticationError:
        print("❌ SMTP authentication failed - check credentials")
        return False
    
    except smtplib.SMTPException as e:
        print(f"❌ SMTP error: {str(e)}")
        return False
    
    except Exception as e:
        print(f"❌ Email send error: {str(e)}")
        return False


def send_sms(body: str) -> bool:
    """
    Send an SMS notification using Twilio.
    
    Args:
        body: SMS message content
    
    Returns:
        bool: True if SMS sent successfully, False otherwise
    """
    settings = get_settings()
    
    # Validate Twilio configuration
    if not settings.TWILIO_SID or not settings.TWILIO_TOKEN or not settings.TWILIO_FROM:
        print("⚠️  Twilio not configured - skipping SMS notification")
        return False
    
    if not settings.ALERT_RECIPIENT_PHONE:
        print("⚠️  No recipient phone configured - skipping SMS notification")
        return False
    
    try:
        # Import Twilio client (lazy import in case not installed)
        from twilio.rest import Client
        
        # Create Twilio client
        client = Client(settings.TWILIO_SID, settings.TWILIO_TOKEN)
        
        # Send SMS
        message = client.messages.create(
            body=body,
            from_=settings.TWILIO_FROM,
            to=settings.ALERT_RECIPIENT_PHONE
        )
        
        print(f"✅ SMS sent to {settings.ALERT_RECIPIENT_PHONE} (SID: {message.sid})")
        return True
    
    except ImportError:
        print("❌ Twilio library not installed - run: pip install twilio")
        return False
    
    except Exception as e:
        print(f"❌ SMS send error: {str(e)}")
        return False


def send_alert(alert_type: str, message: str) -> Tuple[bool, bool, Optional[int]]:
    """
    Send an alert via both email and SMS, then log to database.
    
    Args:
        alert_type: Type of alert (e.g., "movement", "sound", "risk")
        message: Alert message content
    
    Returns:
        Tuple of (email_success, sms_success, log_id)
            - email_success: Whether email was sent successfully
            - sms_success: Whether SMS was sent successfully
            - log_id: Database log ID (None if logging failed)
    """
    print(f"\n🔔 Sending alert: {alert_type}")
    print(f"Message: {message}")
    
    # Send email notification
    email_success = send_email(
        subject=f"Baby Monitor Alert: {alert_type.upper()}",
        body=message
    )
    
    # Send SMS notification
    # Truncate message if too long for SMS (160 char limit)
    sms_message = message if len(message) <= 160 else message[:157] + "..."
    sms_success = send_sms(sms_message)
    
    # Determine if alert was delivered successfully
    # Consider delivered if at least one channel succeeded
    delivered = email_success or sms_success
    
    # Log alert to database
    log_id = None
    try:
        with get_session() as session:
            alert_log = AlertLog(
                alert_type=alert_type,
                message=message,
                delivered=delivered
            )
            session.add(alert_log)
            session.commit()
            session.refresh(alert_log)
            log_id = alert_log.id
            print(f"📝 Alert logged to database (ID: {log_id})")
    
    except Exception as e:
        print(f"❌ Failed to log alert to database: {str(e)}")
    
    # Summary
    if email_success and sms_success:
        print("✅ Alert sent successfully via email and SMS")
    elif email_success:
        print("⚠️  Alert sent via email only (SMS failed)")
    elif sms_success:
        print("⚠️  Alert sent via SMS only (email failed)")
    else:
        print("❌ Alert delivery failed on all channels")
    
    return email_success, sms_success, log_id


def send_test_alert() -> None:
    """
    Send a test alert to verify notification configuration.
    Useful for testing during setup.
    """
    test_message = (
        "🧪 Baby Monitor Test Alert\n\n"
        "This is a test notification from your baby monitoring system. "
        "If you receive this message, your notification settings are configured correctly.\n\n"
        "System ready to monitor your baby!"
    )
    
    email_ok, sms_ok, log_id = send_alert(
        alert_type="test",
        message=test_message
    )
    
    print("\n" + "=" * 50)
    print("TEST ALERT SUMMARY")
    print("=" * 50)
    print(f"Email delivery: {'✅ Success' if email_ok else '❌ Failed'}")
    print(f"SMS delivery: {'✅ Success' if sms_ok else '❌ Failed'}")
    print(f"Database log: {'✅ Logged (ID: {})'.format(log_id) if log_id else '❌ Failed'}")
    print("=" * 50)


def send_risk_alert(risk_level: str, position: str, notes: str) -> Tuple[bool, bool, Optional[int]]:
    """
    Send a risk-based alert with formatted message.
    
    Includes cooldown logic to prevent alert spam.
    
    Args:
        risk_level: Risk level (safe, monitor, caution, alert)
        position: Baby's position description
        notes: Additional notes from analysis
    
    Returns:
        Tuple of (email_success, sms_success, log_id)
    """
    from datetime import datetime
    
    # Map risk level to alert type for cooldown
    risk_to_alert_type = {
        "alert": AlertType.HIGH_RISK,
        "danger": AlertType.HIGH_RISK,
        "caution": AlertType.BABY_DISTRESSED,
        "monitor": AlertType.BABY_DISTRESSED,
        "safe": AlertType.GENERAL
    }
    
    cooldown_type = risk_to_alert_type.get(risk_level.lower(), AlertType.GENERAL)
    
    # Check cooldown
    alert_manager = get_alert_manager()
    if not alert_manager.should_send_alert(cooldown_type):
        print(f"\n🔕 Risk alert skipped due to cooldown: {risk_level}")
        status = alert_manager.get_cooldown_status(cooldown_type)
        remaining = status['cooldown_remaining_seconds']
        print(f"   Retry available in: {int(remaining/60)}m {int(remaining%60)}s")
        return False, False, None
    
    risk_emojis = {
        "safe": "✅",
        "monitor": "👀",
        "caution": "⚠️",
        "alert": "🚨"
    }
    
    emoji = risk_emojis.get(risk_level.lower(), "ℹ️")
    timestamp = datetime.now().strftime("%I:%M %p")
    
    message = (
        f"{emoji} Baby Monitor Alert\n\n"
        f"Time: {timestamp}\n"
        f"Risk Level: {risk_level.upper()}\n"
        f"Position: {position}\n"
        f"Notes: {notes}\n\n"
        f"Please check the baby monitor."
    )
    
    print(f"\n📤 Sending risk alert: {risk_level} ({cooldown_type})")
    email_ok, sms_ok, log_id = send_alert(alert_type=f"risk_{risk_level}", message=message)
    
    # Record successful alert
    if email_ok or sms_ok:
        alert_manager.record_alert_sent(cooldown_type)
        print(f"✅ Risk alert sent and cooldown timer started")
    
    return email_ok, sms_ok, log_id


def send_movement_alert(movement_level: str, position: str) -> Tuple[bool, bool, Optional[int]]:
    """
    Send a movement-based alert with formatted message.
    
    Includes cooldown logic to prevent alert spam.
    
    Args:
        movement_level: Movement level (none, minimal, low, moderate, high)
        position: Baby's position description
    
    Returns:
        Tuple of (email_success, sms_success, log_id)
    """
    from datetime import datetime
    
    # High movement gets its own type, others are general
    cooldown_type = AlertType.HIGH_MOVEMENT if movement_level.lower() == "high" else AlertType.GENERAL
    
    # Check cooldown
    alert_manager = get_alert_manager()
    if not alert_manager.should_send_alert(cooldown_type):
        print(f"\n🔕 Movement alert skipped due to cooldown: {movement_level}")
        status = alert_manager.get_cooldown_status(cooldown_type)
        remaining = status['cooldown_remaining_seconds']
        print(f"   Retry available in: {int(remaining/60)}m {int(remaining%60)}s")
        return False, False, None
    
    timestamp = datetime.now().strftime("%I:%M %p")
    
    message = (
        f"👶 Baby Movement Detected\n\n"
        f"Time: {timestamp}\n"
        f"Movement Level: {movement_level.upper()}\n"
        f"Position: {position}\n\n"
        f"Baby is active. Check monitor for details."
    )
    
    print(f"\n📤 Sending movement alert: {movement_level} ({cooldown_type})")
    email_ok, sms_ok, log_id = send_alert(alert_type="movement", message=message)
    
    # Record successful alert
    if email_ok or sms_ok:
        alert_manager.record_alert_sent(cooldown_type)
        print(f"✅ Movement alert sent and cooldown timer started")
    
    return email_ok, sms_ok, log_id


if __name__ == "__main__":
    # Test notification system
    import sys
    
    print("=" * 50)
    print("BABY MONITOR NOTIFICATION TEST")
    print("=" * 50)
    print("\nThis will send test notifications to configured recipients.")
    print("Make sure you have set up .env with SMTP and/or Twilio credentials.\n")
    
    response = input("Send test notifications? (y/n): ")
    
    if response.lower() == 'y':
        send_test_alert()
    else:
        print("\nTest cancelled. To test individual functions:")
        print("  - send_email('Test Subject', 'Test Body')")
        print("  - send_sms('Test SMS Message')")
        print("  - send_alert('test', 'Test Alert Message')")
