"""
Baby Monitor with Phone Camera via IP Webcam
Uses IP Webcam app to capture frames from phone camera and send to API.
"""
import time
import sys
import cv2
import httpx
import argparse

def capture_from_ip_webcam(ip_webcam_url: str, server_url: str, interval: int = 5):
    """
    Capture frames from IP Webcam app and send to baby monitor API.
    
    Args:
        ip_webcam_url: URL of IP Webcam stream (e.g., http://192.168.1.100:8080)
        server_url: Baby monitor API endpoint
        interval: Seconds between captures
    """
    print("=" * 60)
    print("BABY MONITOR - PHONE CAMERA INTEGRATION")
    print("=" * 60)
    print(f"IP Webcam URL: {ip_webcam_url}")
    print(f"Server URL: {server_url}")
    print(f"Frame Interval: {interval} seconds")
    print("=" * 60)
    print("\nMake sure:")
    print("1. IP Webcam app is running on your phone")
    print("2. Your phone and computer are on the same WiFi network")
    print("3. The baby monitor API is running")
    print("\nPress Ctrl+C to stop\n")
    
    # Build the video feed URL
    video_url = f"{ip_webcam_url}/video"
    
    frame_count = 0
    success_count = 0
    fail_count = 0
    
    try:
        # Open video stream
        print(f"📹 Connecting to phone camera at {video_url}...")
        cap = cv2.VideoCapture(video_url)
        
        if not cap.isOpened():
            print(f"❌ Failed to connect to IP Webcam at {video_url}")
            print("\nTroubleshooting:")
            print("1. Check the IP address is correct")
            print("2. Make sure IP Webcam app is running and server is started")
            print("3. Ensure both devices are on the same WiFi network")
            print(f"4. Try opening {ip_webcam_url} in your browser")
            return
        
        print(f"✅ Connected to phone camera successfully!\n")
        
        while True:
            try:
                # Capture frame
                print(f"[Frame {frame_count + 1}] Capturing from phone...")
                ret, frame = cap.read()
                
                if not ret or frame is None:
                    print("⚠️  Failed to capture frame")
                    fail_count += 1
                    time.sleep(interval)
                    continue
                
                # Encode frame as JPEG
                success, buffer = cv2.imencode('.jpg', frame, [cv2.IMWRITE_JPEG_QUALITY, 85])
                
                if not success:
                    print("⚠️  Failed to encode frame")
                    fail_count += 1
                    time.sleep(interval)
                    continue
                
                frame_bytes = buffer.tobytes()
                
                # Show frame info
                height, width = frame.shape[:2]
                size_kb = len(frame_bytes) / 1024
                print(f"   📸 Captured: {width}x{height}, {size_kb:.1f} KB")
                
                # Post to server
                print(f"   📤 Sending to baby monitor API...")
                
                files = {'file': ('frame.jpg', frame_bytes, 'image/jpeg')}
                
                with httpx.Client(timeout=30.0) as client:
                    response = client.post(server_url, files=files)
                    
                    if response.status_code == 200:
                        result = response.json()
                        success_count += 1
                        
                        print(f"   ✅ Analysis complete!")
                        
                        # Show key results
                        if 'analysis' in result:
                            analysis = result['analysis']
                            baby_detected = analysis.get('baby_detected', False)
                            risk = analysis.get('risk', 'unknown')
                            movement = analysis.get('movement_level', 'unknown')
                            
                            print(f"      Baby: {'✓ Detected' if baby_detected else '✗ Not detected'}")
                            print(f"      Risk: {risk}")
                            print(f"      Movement: {movement}")
                        
                        # Check for alerts
                        if result.get('alert'):
                            print(f"      🚨 ALERT: {result.get('reason')}")
                        else:
                            print(f"      ✓ Safe")
                    
                    else:
                        print(f"   ❌ Server error: {response.status_code}")
                        fail_count += 1
                
                frame_count += 1
                
                # Stats every 10 frames
                if frame_count % 10 == 0:
                    success_rate = (success_count / frame_count * 100) if frame_count > 0 else 0
                    print(f"\n📊 Stats: {frame_count} frames | {success_count} success | {fail_count} failed | {success_rate:.1f}% success rate\n")
                
                # Wait for next capture
                print(f"   ⏳ Waiting {interval}s until next frame...\n")
                time.sleep(interval)
            
            except KeyboardInterrupt:
                raise
            
            except Exception as e:
                print(f"❌ Error: {e}")
                fail_count += 1
                time.sleep(interval)
    
    except KeyboardInterrupt:
        print("\n\n🛑 Stopped by user")
    
    except Exception as e:
        print(f"\n❌ Fatal error: {e}")
        import traceback
        traceback.print_exc()
    
    finally:
        if 'cap' in locals():
            cap.release()
        
        print("\n" + "=" * 60)
        print("Phone camera monitoring stopped")
        print(f"Total frames: {frame_count} | Success: {success_count} | Failed: {fail_count}")
        print("=" * 60)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Baby Monitor with Phone Camera")
    parser.add_argument(
        "--phone-ip",
        type=str,
        required=True,
        help="IP Webcam URL (e.g., http://192.168.1.100:8080)"
    )
    parser.add_argument(
        "--server",
        type=str,
        default="http://127.0.0.1:8000/api/v1/frames/",
        help="API server URL (default: http://127.0.0.1:8000/api/v1/frames/)"
    )
    parser.add_argument(
        "--interval",
        type=int,
        default=5,
        help="Seconds between captures (default: 5)"
    )
    
    args = parser.parse_args()
    
    print("\n🚀 Starting phone camera monitoring...\n")
    
    capture_from_ip_webcam(
        ip_webcam_url=args.phone_ip,
        server_url=args.server,
        interval=args.interval
    )

