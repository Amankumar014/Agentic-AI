"""
Test script for the LangGraph workflow integration with FastAPI.
Demonstrates how the API now uses the workflow as an orchestrator.
"""
import requests
from pathlib import Path
from PIL import Image
import io


def test_workflow_endpoint():
    """Test the /api/v1/frames/ endpoint with the LangGraph workflow."""
    
    # API endpoint
    url = "http://localhost:8000/api/v1/frames/"
    
    # Create a test image
    print("📸 Creating test image...")
    img = Image.new('RGB', (640, 480), color='blue')
    buffer = io.BytesIO()
    img.save(buffer, format='JPEG')
    buffer.seek(0)
    
    # Prepare multipart form data
    files = {
        'file': ('test_frame.jpg', buffer, 'image/jpeg')
    }
    
    print(f"🚀 Sending frame to API: {url}")
    print("   This will trigger the LangGraph workflow:")
    print("   CameraInput → Vision → Audio → Decision → Alert → Logger\n")
    
    try:
        # Send request
        response = requests.post(url, files=files, timeout=60)
        
        # Check response
        if response.status_code == 200:
            result = response.json()
            
            print("\n" + "=" * 70)
            print("✅ WORKFLOW COMPLETED SUCCESSFULLY")
            print("=" * 70)
            
            print(f"\nStatus: {result.get('status')}")
            print(f"Timestamp: {result.get('timestamp')}")
            
            # Vision analysis
            if result.get('analysis'):
                analysis = result['analysis']
                print(f"\n📹 Vision Analysis:")
                print(f"   Baby Detected: {analysis.get('baby_detected')}")
                print(f"   Risk: {analysis.get('risk')}")
                print(f"   Movement: {analysis.get('movement_level')}")
                print(f"   Position: {analysis.get('position')}")
            
            # Audio analysis
            if result.get('audio'):
                audio = result['audio']
                print(f"\n🔊 Audio Analysis:")
                print(f"   Crying: {audio.get('is_crying')}")
                print(f"   Confidence: {audio.get('confidence', 0):.2%}")
            
            # Decision
            if result.get('decision'):
                decision = result['decision']
                print(f"\n🧠 Decision:")
                print(f"   Alert: {'🚨 YES' if decision.get('alert') else '✅ NO'}")
                print(f"   Reason: {decision.get('reason')}")
            
            # Alert result
            if result.get('alert'):
                print(f"\n📢 Alert Status:")
                print(f"   Sent: {'✅ Yes' if result.get('alert_sent') else '❌ No'}")
                if result.get('reason'):
                    print(f"   Reason: {result.get('reason')}")
            
            # Log IDs
            if result.get('log_ids'):
                print(f"\n📝 Database Logs:")
                for key, value in result['log_ids'].items():
                    print(f"   {key}: {value}")
            
            # Errors
            if result.get('errors'):
                print(f"\n⚠️  Errors ({len(result['errors'])}):")
                for error in result['errors']:
                    print(f"   - {error}")
            
            print("\n" + "=" * 70)
            
        else:
            print(f"\n❌ Error: Status {response.status_code}")
            print(f"Response: {response.text}")
    
    except requests.exceptions.ConnectionError:
        print("\n❌ Cannot connect to API server")
        print("   Make sure the server is running: python main.py")
    
    except requests.exceptions.Timeout:
        print("\n❌ Request timeout")
        print("   The workflow may take 10-30 seconds to complete")
    
    except Exception as e:
        print(f"\n❌ Error: {e}")


def test_workflow_with_audio():
    """Test the endpoint with both frame and audio."""
    
    url = "http://localhost:8000/api/v1/frames/with-audio/"
    
    # Create test image
    print("📸 Creating test image...")
    img = Image.new('RGB', (640, 480), color='red')
    img_buffer = io.BytesIO()
    img.save(img_buffer, format='JPEG')
    img_buffer.seek(0)
    
    # Create test audio (placeholder - would need actual WAV data)
    print("🎤 Creating test audio...")
    audio_buffer = io.BytesIO(b'RIFF' + b'\x00' * 100)  # Minimal WAV header
    audio_buffer.seek(0)
    
    # Prepare multipart form data with both files
    files = {
        'file': ('test_frame.jpg', img_buffer, 'image/jpeg'),
        'audio': ('test_audio.wav', audio_buffer, 'audio/wav')
    }
    
    print(f"🚀 Sending frame + audio to API: {url}\n")
    
    try:
        response = requests.post(url, files=files, timeout=60)
        
        if response.status_code == 200:
            result = response.json()
            print(f"✅ Success! Workflow processed both frame and audio")
            print(f"   Status: {result.get('status')}")
            print(f"   Alert: {result.get('alert')}")
        else:
            print(f"❌ Error: {response.status_code}")
            print(f"   {response.text}")
    
    except Exception as e:
        print(f"❌ Error: {e}")


if __name__ == "__main__":
    import sys
    
    print("\n" + "=" * 70)
    print("LANGGRAPH WORKFLOW API TEST")
    print("=" * 70)
    print("\nThis tests the FastAPI endpoint that uses LangGraph workflow")
    print("The endpoint acts as an orchestrator, delegating to the workflow\n")
    
    if len(sys.argv) > 1 and sys.argv[1] == "--with-audio":
        test_workflow_with_audio()
    else:
        test_workflow_endpoint()
        
        print("\n💡 Tip: Run with --with-audio to test audio integration")
        print("   python test_workflow_api.py --with-audio")

