"""
Camera loop for capturing and posting frames to the API.
Continuously captures frames from a camera and sends them for analysis.
"""
import time
import sys
from typing import Optional
import cv2
import httpx

from src.config import get_settings
from src.utils import save_bytes_to_temp


def capture_frame(camera: cv2.VideoCapture) -> Optional[bytes]:
    """
    Capture a single frame from the camera and encode as JPEG.
    
    Args:
        camera: OpenCV VideoCapture object
    
    Returns:
        bytes: JPEG-encoded frame bytes, or None on failure
    """
    try:
        ret, frame = camera.read()
        
        if not ret or frame is None:
            print("⚠️  Failed to capture frame from camera")
            return None
        
        # Encode frame as JPEG
        success, buffer = cv2.imencode('.jpg', frame, [cv2.IMWRITE_JPEG_QUALITY, 85])
        
        if not success:
            print("⚠️  Failed to encode frame as JPEG")
            return None
        
        return buffer.tobytes()
    
    except Exception as e:
        print(f"❌ Error capturing frame: {e}")
        return None


def post_frame_to_server(frame_bytes: bytes, server_url: str, timeout: float = 30.0) -> bool:
    """
    Post a frame to the server as multipart form-data.
    
    Args:
        frame_bytes: JPEG-encoded frame bytes
        server_url: URL of the API endpoint
        timeout: Request timeout in seconds
    
    Returns:
        bool: True if posted successfully, False otherwise
    """
    try:
        # Prepare multipart form data
        files = {
            'file': ('frame.jpg', frame_bytes, 'image/jpeg')
        }
        
        # Use synchronous httpx client
        with httpx.Client(timeout=timeout) as client:
            response = client.post(server_url, files=files)
            
            # Check response
            if response.status_code == 200:
                try:
                    result = response.json()
                    print(f"✅ Frame posted successfully")
                    
                    analysis = result.get("analysis") or {}
                    if analysis:
                        final_state = analysis.get("final_state", "unknown")
                        risk = analysis.get("risk", "unknown")
                        movement = analysis.get("movement_level", "unknown")
                        notes = analysis.get("notes")
                        print(f"   • State: {final_state} | Risk: {risk} | Movement: {movement}")
                        if notes:
                            print(f"   • Notes: {notes}")
                    
                    # Log key response details
                    if 'alert' in result:
                        alert = result.get('alert', False)
                        reason = result.get('alert_reason') or result.get('reason', 'N/A')
                        if alert:
                            print(f"   🚨 ALERT: {reason}")
                        else:
                            print(f"   ✓ Safe: {reason}")
                    
                    return True
                
                except Exception as e:
                    print(f"⚠️  Response received but failed to parse JSON: {e}")
                    print(f"   Raw response: {response.text[:200]}")
                    return True  # Still consider it success if server received it
            
            else:
                print(f"❌ Server returned status {response.status_code}")
                print(f"   Response: {response.text[:200]}")
                return False
    
    except httpx.TimeoutException:
        print(f"❌ Request timeout after {timeout}s")
        return False
    
    except httpx.ConnectError:
        print(f"❌ Cannot connect to server at {server_url}")
        print("   Is the API server running?")
        return False
    
    except Exception as e:
        print(f"❌ Error posting frame: {e}")
        return False


def stream_and_post(
    local_camera_index: int = 0,
    server_url: str = "http://127.0.0.1:8000/api/v1/frames/",
    save_local: bool = False
) -> None:
    """
    Continuously capture frames from camera and post to server.
    
    Args:
        local_camera_index: Camera device index (default: 0)
        server_url: API endpoint URL
        save_local: Whether to save frames locally in temp/ (default: False)
    """
    settings = get_settings()
    interval = settings.FRAME_ANALYZE_INTERVAL
    
    print("=" * 60)
    print("BABY MONITOR - CAMERA LOOP")
    print("=" * 60)
    print(f"Camera Index: {local_camera_index}")
    print(f"Server URL: {server_url}")
    print(f"Frame Interval: {interval} seconds")
    print(f"Save Locally: {save_local}")
    print("=" * 60)
    print("\nPress Ctrl+C to stop\n")
    
    camera = None
    retry_count = 0
    max_retries = 5
    
    try:
        # Open camera
        print(f"📹 Opening camera {local_camera_index}...")
        camera = cv2.VideoCapture(local_camera_index)
        
        if not camera.isOpened():
            print(f"❌ Failed to open camera {local_camera_index}")
            print("   Available cameras: Try indices 0, 1, 2...")
            return
        
        # Get camera properties
        width = int(camera.get(cv2.CAP_PROP_FRAME_WIDTH))
        height = int(camera.get(cv2.CAP_PROP_FRAME_HEIGHT))
        fps = camera.get(cv2.CAP_PROP_FPS)
        
        print(f"✅ Camera opened successfully")
        print(f"   Resolution: {width}x{height}")
        print(f"   FPS: {fps:.1f}")
        print()
        
        frame_count = 0
        success_count = 0
        fail_count = 0
        
        while True:
            try:
                # Capture frame
                print(f"[Frame {frame_count + 1}] Capturing...")
                frame_bytes = capture_frame(camera)
                
                if frame_bytes is None:
                    print("⚠️  Skipping frame due to capture error")
                    fail_count += 1
                    retry_count += 1
                    
                    # If too many consecutive failures, try to reopen camera
                    if retry_count >= max_retries:
                        print(f"⚠️  Too many failures ({retry_count}), attempting to reopen camera...")
                        camera.release()
                        time.sleep(2)
                        camera = cv2.VideoCapture(local_camera_index)
                        
                        if not camera.isOpened():
                            print("❌ Failed to reopen camera. Exiting.")
                            break
                        
                        retry_count = 0
                        print("✅ Camera reopened successfully")
                    
                    time.sleep(interval)
                    continue
                
                # Save locally if requested
                if save_local:
                    try:
                        filepath = save_bytes_to_temp(frame_bytes, suffix=".jpg")
                        print(f"   💾 Saved locally: {filepath}")
                    except Exception as e:
                        print(f"   ⚠️  Failed to save locally: {e}")
                
                # Post to server
                print(f"   📤 Posting to {server_url}...")
                success = post_frame_to_server(frame_bytes, server_url)
                
                if success:
                    success_count += 1
                    retry_count = 0  # Reset retry counter on success
                else:
                    fail_count += 1
                    retry_count += 1
                
                frame_count += 1
                
                # Print stats every 10 frames
                if frame_count % 10 == 0:
                    success_rate = (success_count / frame_count * 100) if frame_count > 0 else 0
                    print(f"\n📊 Stats: {frame_count} frames | {success_count} success | {fail_count} failed | {success_rate:.1f}% success rate\n")
                
                # Wait for next interval
                print(f"   ⏳ Waiting {interval}s until next frame...\n")
                time.sleep(interval)
            
            except KeyboardInterrupt:
                raise  # Re-raise to be caught by outer handler
            
            except Exception as e:
                print(f"❌ Unexpected error in loop: {e}")
                retry_count += 1
                
                if retry_count >= max_retries:
                    print(f"❌ Too many errors ({retry_count}). Exiting.")
                    break
                
                print(f"   Retrying in {interval}s...")
                time.sleep(interval)
    
    except KeyboardInterrupt:
        print("\n\n🛑 Interrupted by user")
    
    except Exception as e:
        print(f"\n❌ Fatal error: {e}")
        import traceback
        traceback.print_exc()
    
    finally:
        # Cleanup
        if camera is not None:
            camera.release()
            print("📹 Camera released")
        
        print("\n" + "=" * 60)
        print("Camera loop stopped")
        print("=" * 60)


def test_camera(camera_index: int = 0) -> bool:
    """
    Test if a camera is accessible and can capture frames.
    
    Args:
        camera_index: Camera device index to test
    
    Returns:
        bool: True if camera works, False otherwise
    """
    print(f"Testing camera {camera_index}...")
    
    try:
        camera = cv2.VideoCapture(camera_index)
        
        if not camera.isOpened():
            print(f"❌ Camera {camera_index} could not be opened")
            return False
        
        # Try to capture a frame
        ret, frame = camera.read()
        camera.release()
        
        if not ret or frame is None:
            print(f"❌ Camera {camera_index} opened but failed to capture frame")
            return False
        
        height, width = frame.shape[:2]
        print(f"✅ Camera {camera_index} works! Resolution: {width}x{height}")
        return True
    
    except Exception as e:
        print(f"❌ Error testing camera {camera_index}: {e}")
        return False


def list_available_cameras(max_test: int = 5) -> list:
    """
    Test multiple camera indices to find available cameras.
    
    Args:
        max_test: Maximum number of indices to test (default: 5)
    
    Returns:
        list: List of working camera indices
    """
    print(f"Scanning for available cameras (testing indices 0-{max_test-1})...\n")
    
    available = []
    for i in range(max_test):
        if test_camera(i):
            available.append(i)
        print()
    
    if available:
        print(f"✅ Found {len(available)} available camera(s): {available}")
    else:
        print("❌ No cameras found")
    
    return available


if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="Baby Monitor Camera Loop")
    parser.add_argument(
        "--camera",
        type=int,
        default=0,
        help="Camera device index (default: 0)"
    )
    parser.add_argument(
        "--server",
        type=str,
        default="http://127.0.0.1:8000/api/v1/frames/",
        help="API server URL (default: http://127.0.0.1:8000/api/v1/frames/)"
    )
    parser.add_argument(
        "--save-local",
        action="store_true",
        help="Save frames locally in temp/ directory"
    )
    parser.add_argument(
        "--test",
        action="store_true",
        help="Test camera and exit"
    )
    parser.add_argument(
        "--list-cameras",
        action="store_true",
        help="List available cameras and exit"
    )
    
    args = parser.parse_args()
    
    # List cameras mode
    if args.list_cameras:
        list_available_cameras()
        sys.exit(0)
    
    # Test camera mode
    if args.test:
        success = test_camera(args.camera)
        sys.exit(0 if success else 1)
    
    # Normal mode - start camera loop
    print("\n🚀 Starting camera loop...")
    print("Make sure the API server is running!\n")
    
    stream_and_post(
        local_camera_index=args.camera,
        server_url=args.server,
        save_local=args.save_local
    )
