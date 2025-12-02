"""
Azure OpenAI Vision integration for image analysis.
Analyzes baby monitor frames using Azure GPT-4 Vision.
"""
import base64
import json
import re
from typing import Dict, Any, Optional, List

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
- baby_detected: CRITICAL - Set to TRUE if you can see ANY of the following in the image:
  * A baby, infant, or small child (any age from newborn to toddler)
  * Any part of a baby (face, body, limbs, even if partially visible)
  * A baby in any position (lying down, sitting, standing, being held, in a crib, on a bed, etc.)
  * A baby in any lighting condition (bright, dim, shadows are OK)
  * A baby at any angle or distance (close-up, far away, side view, top view, etc.)
  * A baby wearing any clothing or wrapped in blankets
  * A baby that is moving or still
  * A baby that is crying, sleeping, or awake
  ONLY set to FALSE if you are CERTAIN there is NO baby, infant, or child visible anywhere in the image.
  When in doubt, set to TRUE - it's better to detect a baby that might not be there than to miss one.

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


FINAL_STATES = [
    "sleeping",
    "awake",
    "crying",
    "distressed",
    "in_unsafe_posture",
    "missing_from_frame",
    "adult_intrusion",
]

MULTIMODAL_SYSTEM_PROMPT = """You are the final decision layer of a baby monitoring system. 
You receive: 
1) Structured sensor outputs (YOLO detections, pose, movement, emotion, face mesh, iris tracking)
2) The actual frame image

NEW CAPABILITIES:
- Face Mesh: 468 facial landmarks, eye aspect ratio (EAR), mouth aspect ratio (MAR), head orientation, face-down detection
- Iris Tracking: Precise eye openness, gaze direction, blinking frequency, eye-closure patterns for sleep detection

TASK: Fuse all information and produce a SINGLE JSON object (no markdown) with:
{
  "final_state": one of ["sleeping","awake","crying","distressed","in_unsafe_posture","missing_from_frame","adult_intrusion"],
  "confidence": float 0-1,
  "baby_detected": boolean,
  "adult_detected": boolean,
  "adult_intrusion": boolean,
  "risk": one of ["safe","monitor","caution","alert"],
  "movement_level": string summary (still/micro/active/major/sudden_jerk),
  "notes": short string referencing *specific* evidence,
  "reasoning": concise explanation referencing the sensor evidence,
  "recommended_action": string describing what caregivers should do,
  "status_flags": array of short bullet strings summarizing notable signals
}

Rules:
- Never make up signals that sensors did not report.
- **SLEEP DETECTION**: Use face mesh eyes_state + iris closure_pattern. If both report "closed" or "sleeping", baby is likely sleeping.
- **CRYING DETECTION**: Use emotion + face mesh mouth_aspect_ratio. High MAR (>0.6) + emotion "crying" = high confidence crying.
- **FACE-DOWN RISK**: If face mesh reports face_down_detected=true, set risk to "alert" and final_state to "in_unsafe_posture".
- **BREATHING MONITORING**: Use face mesh nose_bridge_y changes across frames (if available) to detect breathing irregularities.
- **EARLY DISTRESS**: Use iris tracking blinking frequency and gaze patterns. Abnormal blink rates or rapid eye movements may indicate distress.
- If the baby is missing or occluded, final_state = "missing_from_frame".
- Adult intrusion is TRUE when adult_detected and baby_detected simultaneously.
- Unsafe posture when pose reports rolling/unusual OR face mesh detects face-down.
- Distressed includes pain, uncomfortable, or high movement with crying emotion.
- Adjust risk: sleeping->safe, awake->safe, crying->monitor, distressed/unsafe/adult/missing/face-down->alert.
- Keep JSON valid and lowercase strings as shown.
"""


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
                            "text": "Analyze this baby monitor frame. FIRST, determine if there is a baby, infant, or child visible in the image - look carefully for any human figure, face, body, or limbs that could be a baby. If you see ANY sign of a baby (even partially visible, in shadows, or at unusual angles), set baby_detected to TRUE. THEN, if a baby is detected, look VERY CAREFULLY at the baby's facial expression - is the mouth open? Is the face tense or scrunched? Does the baby appear to be crying or calm? Provide your assessment in JSON format."
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
            parsed_result = parse_vision_response(content)
            
            # Debug: Print warning if baby not detected
            if not parsed_result.get("baby_detected", False) and "error" not in parsed_result:
                print("\n⚠️  WARNING: Baby not detected in frame")
                print(f"   Raw response: {content[:500]}...")
                print(f"   Parsed result: {parsed_result}")
            
            return parsed_result
    
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


async def analyze_multimodal_state(
    image_bytes: bytes,
    fused_context: Dict[str, Any],
    timeout: float = 45.0,
    max_tokens: int = 600,
    debug: bool = False,
) -> Dict[str, Any]:
    """
    Run Azure Vision as the final reasoning layer over multi-agent signals.
    """
    from src.config import get_settings

    settings = get_settings()
    if not (
        settings.AZURE_OPENAI_ENDPOINT
        and settings.AZURE_OPENAI_API_KEY
        and settings.AZURE_OPENAI_DEPLOYMENT
    ):
        fallback = _local_multimodal_reasoning(fused_context)
        fallback["reasoning"] = "Azure not configured - used local fusion"
        return fallback

    try:
        base64_image = base64.b64encode(image_bytes).decode("utf-8")
    except Exception as exc:
        fallback = _local_multimodal_reasoning(fused_context)
        fallback["reasoning"] = f"Image encoding failed ({exc}) - local fusion"
        return fallback

    endpoint = settings.AZURE_OPENAI_ENDPOINT.rstrip("/")
    deployment = settings.AZURE_OPENAI_DEPLOYMENT
    api_version = "2024-02-15-preview"
    url = f"{endpoint}/openai/deployments/{deployment}/chat/completions?api-version={api_version}"

    context_text = json.dumps(_json_safe(fused_context), indent=2)
    payload = {
        "messages": [
            {
                "role": "system",
                "content": MULTIMODAL_SYSTEM_PROMPT,
            },
            {
                "role": "user",
                "content": [
                    {
                        "type": "text",
                        "text": "Sensor summary JSON:\n" + context_text,
                    },
                    {
                        "type": "image_url",
                        "image_url": {"url": f"data:image/jpeg;base64,{base64_image}"},
                    },
                ],
            },
        ],
        "max_tokens": max_tokens,
        "temperature": 0.1,
    }

    headers = {
        "api-key": settings.AZURE_OPENAI_API_KEY,
        "Content-Type": "application/json",
    }

    try:
        async with httpx.AsyncClient(timeout=timeout) as client:
            response = await client.post(url, json=payload, headers=headers)

        if response.status_code != 200:
            raise httpx.HTTPStatusError(
                f"Azure status {response.status_code}: {response.text}",
                request=response.request,
                response=response,
            )

        data = response.json()
        choices = data.get("choices", [])
        if not choices:
            raise ValueError("Azure response missing choices")

        content = choices[0].get("message", {}).get("content", "")
        if debug:
            print("\n" + "=" * 70)
            print("🔍 DEBUG: RAW MULTIMODAL AZURE RESPONSE")
            print("=" * 70)
            print(content)
            print("=" * 70 + "\n")

        parsed = parse_multimodal_response(content)
        if "error" in parsed:
            fallback = _local_multimodal_reasoning(fused_context)
            fallback["reasoning"] = f"Azure parse error: {parsed['error']}"
            fallback["raw_response"] = parsed.get("raw_text")
            return fallback

        parsed["signals_used"] = fused_context
        return parsed

    except (httpx.RequestError, httpx.HTTPStatusError, json.JSONDecodeError, ValueError) as exc:
        fallback = _local_multimodal_reasoning(fused_context)
        fallback["reasoning"] = f"Azure fusion call failed: {exc}"
        return fallback


def parse_multimodal_response(content: str) -> Dict[str, Any]:
    """Parse Azure's multimodal reasoning response."""
    try:
        cleaned = content.strip()
        cleaned = re.sub(r"^```(?:json)?\s*\n", "", cleaned)
        cleaned = re.sub(r"\n```\s*$", "", cleaned)
        payload = json.loads(cleaned)

        required = [
            "final_state",
            "confidence",
            "baby_detected",
            "risk",
            "notes",
            "reasoning",
            "status_flags",
        ]
        missing = [k for k in required if k not in payload]
        if missing:
            return {
                "error": f"Missing keys: {', '.join(missing)}",
                "raw_text": content,
            }

        final_state = str(payload.get("final_state", "awake")).lower()
        if final_state not in FINAL_STATES:
            final_state = "awake"

        confidence = float(payload.get("confidence", 0.6))
        confidence = max(0.0, min(confidence, 1.0))

        status_flags = payload.get("status_flags") or []
        if not isinstance(status_flags, list):
            status_flags = [str(status_flags)]

        result = {
            "final_state": final_state,
            "confidence": confidence,
            "baby_detected": bool(payload.get("baby_detected", False)),
            "adult_detected": bool(payload.get("adult_detected", False)),
            "adult_intrusion": bool(payload.get("adult_intrusion", False)),
            "risk": str(payload.get("risk", "monitor")).lower(),
            "movement_level": payload.get("movement_level", "unknown"),
            "notes": payload.get("notes", ""),
            "reasoning": payload.get("reasoning", ""),
            "recommended_action": payload.get("recommended_action", ""),
            "status_flags": status_flags,
        }
        return result
    except Exception as exc:
        return {
            "error": f"Multimodal parse error: {exc}",
            "raw_text": content,
        }


def _local_multimodal_reasoning(fused_context: Dict[str, Any]) -> Dict[str, Any]:
    """Fallback heuristic fusion when Azure is unavailable."""
    yolo = fused_context.get("yolo_result") or {}
    pose = fused_context.get("pose_result") or {}
    movement = fused_context.get("movement_result") or {}
    emotion = fused_context.get("emotion_result") or {}
    face_mesh = fused_context.get("face_mesh_result") or {}
    iris_tracking = fused_context.get("iris_tracking_result") or {}

    baby_detected = bool(yolo.get("baby_detected") or pose.get("pose_label") in {"sleeping", "sitting", "standing"})
    adult_detected = bool(yolo.get("adult_detected"))
    adult_intrusion = bool(yolo.get("adult_intrusion"))
    pose_label = str(pose.get("pose_label", "unknown")).lower()
    emotion_label = str(emotion.get("emotion_label", "neutral")).lower()
    movement_type = str(movement.get("movement_type", "unknown")).lower()
    sudden = movement.get("sudden_jerk", False)
    
    # Extract face mesh signals
    face_detected = face_mesh.get("face_detected", False) if isinstance(face_mesh, dict) else False
    face_down = face_mesh.get("face_down_detected", False) if isinstance(face_mesh, dict) else False
    eyes_state_mesh = str(face_mesh.get("eyes_state", "unknown")).lower() if isinstance(face_mesh, dict) else "unknown"
    mouth_state_mesh = str(face_mesh.get("mouth_state", "unknown")).lower() if isinstance(face_mesh, dict) else "unknown"
    mouth_aspect_ratio = face_mesh.get("mouth_aspect_ratio", 0.0) if isinstance(face_mesh, dict) else 0.0
    
    # Extract iris tracking signals
    iris_detected = iris_tracking.get("iris_detected", False) if isinstance(iris_tracking, dict) else False
    eyes_state_iris = str(iris_tracking.get("eyes_state", "unknown")).lower() if isinstance(iris_tracking, dict) else "unknown"
    closure_pattern = str(iris_tracking.get("closure_pattern", "unknown")).lower() if isinstance(iris_tracking, dict) else "unknown"
    blink_freq = iris_tracking.get("blinking", {}).get("frequency_per_minute", 0.0) if isinstance(iris_tracking, dict) else 0.0

    # CRITICAL: Check face-down risk first
    if face_down:
        final_state = "in_unsafe_posture"
        risk = "alert"
        status_flags = ["Face-down position detected - immediate risk"]
    elif not baby_detected:
        final_state = "missing_from_frame"
        risk = _derive_risk(final_state)
        status_flags = []
    elif adult_intrusion:
        final_state = "adult_intrusion"
        risk = _derive_risk(final_state)
        status_flags = ["Adult intrusion detected"]
    # Improved sleep detection using face mesh + iris tracking
    elif (eyes_state_mesh == "closed" and closure_pattern in {"sleeping", "drowsy"}) or \
         (eyes_state_iris == "closed" and closure_pattern in {"sleeping", "drowsy"}):
        final_state = "sleeping"
        risk = _derive_risk(final_state)
        status_flags = ["Eyes closed", f"Closure pattern: {closure_pattern}"]
    # Improved crying detection using face mesh + emotion
    elif emotion_label in {"crying", "pain", "distress"} or \
         (mouth_state_mesh == "open" and mouth_aspect_ratio > 0.6):
        # High mouth opening + crying emotion = crying
        if emotion_label in {"crying", "pain"} or mouth_aspect_ratio > 0.65:
            final_state = "crying"
        else:
            final_state = "distressed"
        risk = _derive_risk(final_state)
        status_flags = [f"Emotion: {emotion_label}", f"Mouth open: MAR={mouth_aspect_ratio:.2f}"]
    elif pose_label in {"rolling", "unusual_posture"}:
        final_state = "in_unsafe_posture"
        risk = _derive_risk(final_state)
        status_flags = ["Unusual posture detected"]
    elif emotion_label in {"distress"} or (emotion_label == "uncomfortable" and movement_type in {"major_movement"}):
        final_state = "distressed"
        risk = _derive_risk(final_state)
        status_flags = [f"Emotion: {emotion_label}"]
    # Detect early distress using iris tracking
    elif blink_freq > 40:  # Abnormally high blink rate
        final_state = "distressed"
        risk = "monitor"
        status_flags = [f"Abnormal blink rate: {blink_freq:.1f}/min"]
    elif sudden and emotion_label not in {"happy", "neutral"}:
        final_state = "distressed"
        risk = _derive_risk(final_state)
        status_flags = ["Sudden jerk with negative emotion"]
    elif emotion_label == "happy" or (emotion_label == "neutral" and movement_type in {"active", "major_movement"}):
        final_state = "awake"
        risk = _derive_risk(final_state)
        status_flags = []
    elif movement_type in {"still", "micro_movement"} and emotion_label in {"neutral"}:
        # Check iris tracking for definitive sleep state
        if closure_pattern == "sleeping":
            final_state = "sleeping"
        else:
            final_state = "awake"
        risk = _derive_risk(final_state)
        status_flags = []
    else:
        final_state = "awake"
        risk = _derive_risk(final_state)
        status_flags = []

    # Build notes
    notes = []
    if emotion_label:
        notes.append(f"Emotion: {emotion_label}")
    if pose_label:
        notes.append(f"Pose: {pose_label}")
    if movement_type:
        notes.append(f"Movement: {movement_type}")
    if face_detected:
        notes.append(f"Eyes: {eyes_state_mesh}, Mouth: {mouth_state_mesh}")
    if iris_detected:
        notes.append(f"Iris pattern: {closure_pattern}")
    if adult_intrusion:
        notes.append("Adult present with baby")
    if face_down:
        notes.append("⚠️ FACE-DOWN POSITION")

    # Additional status flags
    if movement.get("stillness_exceeded"):
        status_flags.append("Baby still for extended period")
    if face_down:
        status_flags.append("⚠️ Face-down detected")

    return {
        "final_state": final_state,
        "confidence": 0.7 if (face_detected or iris_detected) else 0.6,
        "baby_detected": baby_detected,
        "adult_detected": adult_detected,
        "adult_intrusion": adult_intrusion,
        "risk": risk,
        "movement_level": movement_type,
        "notes": " | ".join(notes) if notes else "",
        "reasoning": "Local heuristic fusion with face mesh and iris tracking",
        "recommended_action": _recommend_action(final_state),
        "status_flags": status_flags,
        "signals_used": fused_context,
    }


def _derive_risk(final_state: str) -> str:
    mapping = {
        "sleeping": "safe",
        "awake": "safe",  # Changed from "monitor" - baby awake is normal
        "crying": "monitor",  # Monitor for crying, but not immediate alert
        "distressed": "alert",
        "in_unsafe_posture": "alert",
        "missing_from_frame": "alert",
        "adult_intrusion": "alert",
    }
    return mapping.get(final_state, "safe")


def _recommend_action(final_state: str) -> str:
    actions = {
        "sleeping": "No action needed, continue monitoring.",
        "awake": "Baby is awake; monitor or gently soothe if needed.",
        "crying": "Check baby promptly and soothe.",
        "distressed": "Immediate attention required to calm and assess safety.",
        "in_unsafe_posture": "Adjust baby's posture to a safe sleeping position.",
        "missing_from_frame": "Verify camera angle and baby location immediately.",
        "adult_intrusion": "Ensure authorized caregiver is present; investigate intrusion.",
    }
    return actions.get(final_state, "Monitor conditions closely.")


def _json_safe(value: Any):
    if isinstance(value, (str, int, float, bool)) or value is None:
        return value
    if isinstance(value, dict):
        return {str(k): _json_safe(v) for k, v in value.items()}
    if isinstance(value, (list, tuple)):
        return [_json_safe(v) for v in value]
    return str(value)


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
