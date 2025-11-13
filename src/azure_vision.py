"""
Azure OpenAI Vision integration for image analysis.
Analyzes baby monitor frames using Azure GPT-4 Vision.
"""
import base64
import json
import re
from typing import Dict, Any, Optional

import httpx


# System prompt for baby monitoring analysis
BABY_MONITOR_SYSTEM_PROMPT = """You are a baby monitor AI assistant. Analyze the provided image and respond with ONLY a JSON object (no markdown, no code fences).

Your response must be valid JSON with these exact keys:
{
  "baby_detected": boolean,
  "movement_level": string (one of: "none", "minimal", "low", "moderate", "high"),
  "position": string (description of baby's position, e.g., "lying on back", "sitting up", "standing", "not visible"),
  "risk": string (one of: "safe", "monitor", "caution", "alert"),
  "notes": string (brief observations, concerns, or additional context)
}

Guidelines:
- baby_detected: true if you can see a baby/infant in the image

- movement_level: assess based on visible motion blur, posture changes, limb movement

- position: describe the baby's current position/posture (lying on back, on stomach, sitting, standing)

- risk: Assess overall safety level:
  * "safe" = baby is calm, comfortable, in safe position
  * "monitor" = baby shows signs of distress (crying, fussing, uncomfortable) or unusual behavior - watch closely
  * "caution" = unsafe position (face down, blanket over face) or moderate distress
  * "alert" = immediate danger or severe distress

- notes: CRITICAL - Carefully observe and report:
  * Facial expression: Is the baby crying, fussing, smiling, neutral, eyes open/closed?  
  * Signs of distress: crying face, mouth open wide, furrowed brow, tears, red face, tense body . If the baby eyes are closed , hands are upwards and mouth is open, this is a sign that baby is in distress.
  * Comfort level: appears calm/distressed/uncomfortable/content
  * Safety concerns: blanket near face, unsafe position, visible hazards
  * Any unusual observations

CRITICAL INSTRUCTIONS - READ CAREFULLY:
1. FACIAL EXPRESSIONS ARE THE MOST IMPORTANT INDICATOR
2. Look VERY carefully at the baby's face:
   - Is the mouth OPEN WIDE? (crying indicator)
   - Are the eyes SQUEEZED SHUT or showing distress? (crying indicator)
   - Is the face SCRUNCHED, WRINKLED, or showing tension? (crying indicator)
   - Are there TEARS visible? (crying indicator)
   - Is the baby's expression NEUTRAL/PEACEFUL or DISTRESSED/CRYING?

3. CRYING DETECTION:
   - If you see ANY of the above signs, the baby IS CRYING or DISTRESSED
   - Set risk to AT LEAST "monitor" for any distress
   - CLEARLY STATE "baby is crying" or "baby appears distressed" in notes
   - DO NOT say "appears calm" if you see crying indicators

4. COMFORT ASSESSMENT:
   - Calm = peaceful expression, relaxed face, closed mouth, no tension
   - Distressed = open mouth, scrunched face, tense body, any crying signs

If there is ANY doubt about whether the baby is crying, describe what you see in detail and lean toward "monitor" risk level for safety.

Respond with ONLY the JSON object, no other text."""


async def analyze_image_bytes(
    image_bytes: bytes,
    timeout: float = 30.0,
    max_tokens: int = 500,
    debug: bool = False
) -> Dict[str, Any]:
    """
    Analyze an image using Azure OpenAI Vision API.
    
    Args:
        image_bytes: Raw image bytes (JPEG, PNG, etc.)
        timeout: Request timeout in seconds (default: 30.0)
        max_tokens: Maximum tokens in response (default: 500)
    
    Returns:
        Dict containing:
            - On success: parsed JSON with baby_detected, movement_level, position, risk, notes
            - On parse failure: {"error": str, "raw_text": str, "baby_detected": False}
            - On API failure: {"error": str, "baby_detected": False}
    """
    from src.config import get_settings
    
    settings = get_settings()
    
    # Validate configuration
    if not settings.AZURE_OPENAI_ENDPOINT:
        return {
            "error": "Azure OpenAI endpoint not configured",
            "baby_detected": False
        }
    
    if not settings.AZURE_OPENAI_API_KEY:
        return {
            "error": "Azure OpenAI API key not configured",
            "baby_detected": False
        }
    
    if not settings.AZURE_OPENAI_DEPLOYMENT:
        return {
            "error": "Azure OpenAI deployment not configured",
            "baby_detected": False
        }
    
    try:
        # Encode image to base64
        base64_image = base64.b64encode(image_bytes).decode('utf-8')
        
        # Construct the API URL
        # Azure OpenAI endpoint format: https://<resource>.openai.azure.com/openai/deployments/<deployment>/chat/completions?api-version=<version>
        endpoint = settings.AZURE_OPENAI_ENDPOINT.rstrip('/')
        deployment = settings.AZURE_OPENAI_DEPLOYMENT
        api_version = "2024-02-15-preview"  # Vision-capable API version
        
        url = f"{endpoint}/openai/deployments/{deployment}/chat/completions?api-version={api_version}"
        
        # Prepare the request payload
        payload = {
            "messages": [
                {
                    "role": "system",
                    "content": BABY_MONITOR_SYSTEM_PROMPT
                },
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "image_url",
                            "image_url": {
                                "url": f"data:image/jpeg;base64,{base64_image}"
                            }
                        },
                        {
                            "type": "text",
                            "text": "Analyze this baby monitor frame. Look VERY CAREFULLY at the baby's facial expression - is the mouth open? Is the face tense or scrunched? Does the baby appear to be crying or calm? Provide your assessment in JSON format."
                        }
                    ]
                }
            ],
            "max_tokens": max_tokens,
            "temperature": 0.0,  # Zero temperature for deterministic, focused analysis
        }
        
        # Headers for Azure OpenAI
        headers = {
            "api-key": settings.AZURE_OPENAI_API_KEY,
            "Content-Type": "application/json"
        }
        
        # Make async HTTP request
        async with httpx.AsyncClient(timeout=timeout) as client:
            response = await client.post(
                url,
                json=payload,
                headers=headers
            )
            
            # Check for HTTP errors
            if response.status_code != 200:
                error_detail = response.text
                try:
                    error_json = response.json()
                    error_detail = error_json.get("error", {}).get("message", error_detail)
                except Exception:
                    pass
                
                return {
                    "error": f"Azure API error (status {response.status_code}): {error_detail}",
                    "baby_detected": False
                }
            
            # Parse response
            response_data = response.json()
            
            # Extract the content from the response
            if "choices" not in response_data or len(response_data["choices"]) == 0:
                return {
                    "error": "No choices in API response",
                    "raw_response": response_data,
                    "baby_detected": False
                }
            
            content = response_data["choices"][0].get("message", {}).get("content", "")
            
            # Debug mode - print raw response
            if debug:
                print("\n" + "=" * 70)
                print("🔍 DEBUG: RAW AZURE VISION API RESPONSE")
                print("=" * 70)
                print(content)
                print("=" * 70 + "\n")
            
            if not content:
                return {
                    "error": "Empty content in API response",
                    "baby_detected": False
                }
            
            # Parse the JSON response
            return parse_vision_response(content)
    
    except httpx.TimeoutException:
        return {
            "error": "Request timeout - Azure API did not respond in time",
            "baby_detected": False
        }
    
    except httpx.RequestError as e:
        return {
            "error": f"Network error: {str(e)}",
            "baby_detected": False
        }
    
    except Exception as e:
        return {
            "error": f"Unexpected error: {str(e)}",
            "baby_detected": False
        }


def parse_vision_response(content: str) -> Dict[str, Any]:
    """
    Parse the vision API response content into structured JSON.
    Handles markdown code fences and other formatting issues.
    
    Args:
        content: Raw content string from API response
    
    Returns:
        Dict with parsed JSON or error information
    """
    try:
        # Strip whitespace
        content = content.strip()
        
        # Remove markdown code fences if present
        # Patterns: ```json\n...\n``` or ```\n...\n```
        content = re.sub(r'^```(?:json)?\s*\n', '', content)
        content = re.sub(r'\n```\s*$', '', content)
        content = content.strip()
        
        # Attempt to parse JSON
        parsed = json.loads(content)
        
        # Validate required keys
        required_keys = ["baby_detected", "movement_level", "position", "risk", "notes"]
        missing_keys = [key for key in required_keys if key not in parsed]
        
        if missing_keys:
            return {
                "error": f"Missing required keys: {', '.join(missing_keys)}",
                "raw_text": content,
                "baby_detected": parsed.get("baby_detected", False),
                "partial_data": parsed
            }
        
        # Ensure baby_detected is boolean
        if not isinstance(parsed["baby_detected"], bool):
            parsed["baby_detected"] = str(parsed["baby_detected"]).lower() in ["true", "1", "yes"]
        
        return parsed
    
    except json.JSONDecodeError as e:
        return {
            "error": f"JSON parse error: {str(e)}",
            "raw_text": content,
            "baby_detected": False
        }
    
    except Exception as e:
        return {
            "error": f"Parse error: {str(e)}",
            "raw_text": content,
            "baby_detected": False
        }


async def analyze_image_file(
    file_path: str,
    timeout: float = 30.0
) -> Dict[str, Any]:
    """
    Convenience function to analyze an image file.
    
    Args:
        file_path: Path to image file
        timeout: Request timeout in seconds
    
    Returns:
        Dict with analysis results
    """
    try:
        with open(file_path, 'rb') as f:
            image_bytes = f.read()
        return await analyze_image_bytes(image_bytes, timeout=timeout)
    except FileNotFoundError:
        return {
            "error": f"Image file not found: {file_path}",
            "baby_detected": False
        }
    except Exception as e:
        return {
            "error": f"Error reading image file: {str(e)}",
            "baby_detected": False
        }


if __name__ == "__main__":
    # Test the module
    import asyncio
    
    async def test():
        print("Testing Azure Vision integration...")
        print("\nNote: This requires valid Azure OpenAI credentials in .env")
        
        # Test with a dummy image (small red square)
        # In production, you'd use real camera frames
        from PIL import Image
        import io
        
        # Create a test image
        img = Image.new('RGB', (100, 100), color='red')
        buffer = io.BytesIO()
        img.save(buffer, format='JPEG')
        test_bytes = buffer.getvalue()
        
        print("\nAnalyzing test image...")
        result = await analyze_image_bytes(test_bytes)
        
        print("\nResult:")
        print(json.dumps(result, indent=2))
        
        if "error" in result:
            print(f"\n⚠️  Error occurred: {result['error']}")
        else:
            print("\n✅ Analysis completed successfully!")
    
    asyncio.run(test())
