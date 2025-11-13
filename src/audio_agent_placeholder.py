"""
Audio analysis agent for baby cry detection.
Provides audio recording, feature extraction, and cry classification.

Note: This module requires sounddevice and librosa to be installed.
Install with: pip install sounddevice librosa

For cry detection model:
- Place trained model at: models/cry_detector.joblib
- Model should accept feature vector and return cry probability
"""
import os
import warnings
from pathlib import Path
from typing import Dict, Any, Optional, Tuple
import numpy as np

from src.config import get_settings
from src.utils import save_bytes_to_temp


def record_audio_clip(
    duration: Optional[int] = None,
    sample_rate: Optional[int] = None,
    device: Optional[int] = None
) -> Tuple[np.ndarray, int]:
    """
    Record an audio clip using sounddevice.
    
    Args:
        duration: Recording duration in seconds (default: from settings)
        sample_rate: Sample rate in Hz (default: from settings)
        device: Audio device index (default: system default)
    
    Returns:
        Tuple of (audio_data, sample_rate)
            - audio_data: numpy array of audio samples
            - sample_rate: sample rate used for recording
    
    Raises:
        ImportError: If sounddevice is not installed
        Exception: If recording fails
    
    Note:
        Make sure to install sounddevice: pip install sounddevice
        On Linux, you may need: sudo apt-get install portaudio19-dev python3-pyaudio
    """
    try:
        import sounddevice as sd
    except ImportError:
        raise ImportError(
            "sounddevice is required for audio recording. "
            "Install with: pip install sounddevice"
        )
    
    settings = get_settings()
    
    # Use settings as defaults
    if duration is None:
        duration = settings.AUDIO_DURATION
    if sample_rate is None:
        sample_rate = settings.AUDIO_SAMPLE_RATE
    
    try:
        print(f"🎤 Recording audio for {duration}s at {sample_rate}Hz...")
        
        # Record audio
        audio_data = sd.rec(
            int(duration * sample_rate),
            samplerate=sample_rate,
            channels=1,  # Mono recording
            dtype='float32',
            device=device
        )
        
        # Wait for recording to complete
        sd.wait()
        
        print(f"✅ Audio recorded: {audio_data.shape[0]} samples")
        
        return audio_data.flatten(), sample_rate
    
    except Exception as e:
        print(f"❌ Error recording audio: {e}")
        raise


def save_audio_to_temp(audio_data: np.ndarray, sample_rate: int, suffix: str = ".wav") -> str:
    """
    Save audio data to a temporary WAV file.
    
    Args:
        audio_data: Audio samples as numpy array
        sample_rate: Sample rate in Hz
        suffix: File extension (default: ".wav")
    
    Returns:
        str: Path to saved audio file
    
    Raises:
        ImportError: If scipy is not installed
    """
    try:
        from scipy.io import wavfile
    except ImportError:
        raise ImportError(
            "scipy is required for saving audio. "
            "Install with: pip install scipy"
        )
    
    from src.config import ensure_directories
    import uuid
    from datetime import datetime
    
    # Ensure temp directory exists
    ensure_directories()
    
    # Get project root
    project_root = Path(__file__).parent.parent
    temp_dir = project_root / "temp"
    
    # Generate unique filename
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    unique_id = str(uuid.uuid4())[:8]
    filename = f"audio_{timestamp}_{unique_id}{suffix}"
    filepath = temp_dir / filename
    
    # Normalize audio to int16 range
    audio_int16 = (audio_data * 32767).astype(np.int16)
    
    # Save as WAV
    wavfile.write(str(filepath), sample_rate, audio_int16)
    
    print(f"💾 Audio saved to: {filepath}")
    return str(filepath)


def extract_librosa_features(filepath: str) -> Dict[str, float]:
    """
    Extract audio features using librosa.
    
    Args:
        filepath: Path to audio file
    
    Returns:
        Dict with feature values:
            - mfcc_mean: Mean of MFCC coefficients
            - zcr_mean: Mean zero-crossing rate
            - spectral_centroid_mean: Mean spectral centroid
            - rms_mean: Mean RMS energy
            - tempo: Estimated tempo
    
    Raises:
        ImportError: If librosa is not installed
        Exception: If feature extraction fails
    
    Note:
        Install librosa with: pip install librosa
    """
    try:
        import librosa
    except ImportError:
        raise ImportError(
            "librosa is required for audio feature extraction. "
            "Install with: pip install librosa"
        )
    
    try:
        # Suppress librosa warnings
        with warnings.catch_warnings():
            warnings.simplefilter("ignore")
            
            # Load audio file
            y, sr = librosa.load(filepath, sr=None)
            
            # Extract MFCC (Mel-frequency cepstral coefficients)
            mfccs = librosa.feature.mfcc(y=y, sr=sr, n_mfcc=13)
            mfcc_mean = np.mean(mfccs)
            
            # Zero-crossing rate
            zcr = librosa.feature.zero_crossing_rate(y)
            zcr_mean = np.mean(zcr)
            
            # Spectral centroid
            spectral_centroids = librosa.feature.spectral_centroid(y=y, sr=sr)
            spectral_centroid_mean = np.mean(spectral_centroids)
            
            # RMS (root-mean-square) energy
            rms = librosa.feature.rms(y=y)
            rms_mean = np.mean(rms)
            
            # Tempo estimation
            tempo, _ = librosa.beat.beat_track(y=y, sr=sr)
            
            features = {
                "mfcc_mean": float(mfcc_mean),
                "zcr_mean": float(zcr_mean),
                "spectral_centroid_mean": float(spectral_centroid_mean),
                "rms_mean": float(rms_mean),
                "tempo": float(tempo) if tempo else 0.0
            }
            
            print(f"✅ Extracted features: {list(features.keys())}")
            return features
    
    except Exception as e:
        print(f"❌ Error extracting features: {e}")
        raise


def get_feature_vector(features: Dict[str, float]) -> np.ndarray:
    """
    Convert feature dict to numpy array for model input.
    
    Args:
        features: Feature dictionary from extract_librosa_features
    
    Returns:
        numpy array of features in consistent order
    """
    # Consistent feature order for model
    feature_names = [
        "mfcc_mean",
        "zcr_mean", 
        "spectral_centroid_mean",
        "rms_mean",
        "tempo"
    ]
    
    return np.array([features.get(name, 0.0) for name in feature_names])


def classify_cry(features: Dict[str, float]) -> Dict[str, Any]:
    """
    Classify audio as crying or not using a trained model.
    
    Args:
        features: Feature dictionary from extract_librosa_features
    
    Returns:
        Dict with:
            - is_crying: bool (whether crying was detected)
            - confidence: float (0.0-1.0, model confidence)
            - model_loaded: bool (whether model was found and loaded)
    
    Note:
        Place trained model at: models/cry_detector.joblib
        Model should be a scikit-learn classifier with predict_proba method.
    """
    # Check for model file
    project_root = Path(__file__).parent.parent
    model_path = project_root / "models" / "cry_detector.joblib"
    
    if not model_path.exists():
        print("⚠️  Cry detector model not found at models/cry_detector.joblib")
        print("   Returning default (no cry detected)")
        return {
            "is_crying": False,
            "confidence": 0.0,
            "model_loaded": False,
            "message": "Model not found - place trained model at models/cry_detector.joblib"
        }
    
    try:
        import joblib
    except ImportError:
        print("⚠️  joblib not installed - cannot load model")
        return {
            "is_crying": False,
            "confidence": 0.0,
            "model_loaded": False,
            "message": "joblib not installed - run: pip install joblib"
        }
    
    try:
        # Load model
        model = joblib.load(model_path)
        print(f"✅ Loaded cry detector model from {model_path}")
        
        # Convert features to vector
        feature_vector = get_feature_vector(features)
        feature_vector = feature_vector.reshape(1, -1)  # Shape for prediction
        
        # Make prediction
        prediction = model.predict(feature_vector)[0]
        
        # Get confidence if model supports it
        confidence = 0.5  # Default
        if hasattr(model, 'predict_proba'):
            proba = model.predict_proba(feature_vector)[0]
            confidence = float(proba[1] if len(proba) > 1 else proba[0])
        
        is_crying = bool(prediction)
        
        print(f"🔊 Cry detection result: {is_crying} (confidence: {confidence:.2f})")
        
        return {
            "is_crying": is_crying,
            "confidence": confidence,
            "model_loaded": True
        }
    
    except Exception as e:
        print(f"❌ Error in cry classification: {e}")
        return {
            "is_crying": False,
            "confidence": 0.0,
            "model_loaded": False,
            "error": str(e)
        }


def analyze_audio_file(filepath: str) -> Dict[str, Any]:
    """
    Complete audio analysis pipeline: extract features and classify.
    
    Args:
        filepath: Path to audio file
    
    Returns:
        Dict with features and classification results
    """
    try:
        # Extract features
        features = extract_librosa_features(filepath)
        
        # Classify
        classification = classify_cry(features)
        
        # Combine results
        result = {
            "features": features,
            "classification": classification,
            "is_crying": classification.get("is_crying", False),
            "confidence": classification.get("confidence", 0.0),
            "audio_file": filepath
        }
        
        return result
    
    except Exception as e:
        print(f"❌ Error analyzing audio: {e}")
        return {
            "error": str(e),
            "is_crying": False,
            "confidence": 0.0,
            "audio_file": filepath
        }


def record_and_analyze() -> Dict[str, Any]:
    """
    Complete pipeline: record audio, save, extract features, and classify.
    
    Returns:
        Dict with full analysis results
    """
    try:
        # Record audio
        audio_data, sample_rate = record_audio_clip()
        
        # Save to temp
        filepath = save_audio_to_temp(audio_data, sample_rate)
        
        # Analyze
        result = analyze_audio_file(filepath)
        
        return result
    
    except Exception as e:
        print(f"❌ Error in record and analyze pipeline: {e}")
        return {
            "error": str(e),
            "is_crying": False,
            "confidence": 0.0
        }


def test_audio_system() -> bool:
    """
    Test if audio system is properly configured.
    
    Returns:
        bool: True if audio system works, False otherwise
    """
    print("\n" + "=" * 60)
    print("AUDIO SYSTEM TEST")
    print("=" * 60)
    
    success = True
    
    # Test sounddevice
    print("\n[1/3] Testing sounddevice...")
    try:
        import sounddevice as sd
        devices = sd.query_devices()
        print(f"✅ sounddevice installed")
        print(f"   Available devices: {len(devices)}")
    except ImportError:
        print("❌ sounddevice not installed")
        print("   Install with: pip install sounddevice")
        success = False
    except Exception as e:
        print(f"⚠️  sounddevice error: {e}")
    
    # Test librosa
    print("\n[2/3] Testing librosa...")
    try:
        import librosa
        print(f"✅ librosa installed (version {librosa.__version__})")
    except ImportError:
        print("❌ librosa not installed")
        print("   Install with: pip install librosa")
        success = False
    
    # Test model
    print("\n[3/3] Testing cry detector model...")
    project_root = Path(__file__).parent.parent
    model_path = project_root / "models" / "cry_detector.joblib"
    
    if model_path.exists():
        print(f"✅ Model found at {model_path}")
    else:
        print(f"⚠️  Model not found at {model_path}")
        print("   This is optional - will use placeholder detection")
    
    print("\n" + "=" * 60)
    if success:
        print("✅ Audio system ready!")
    else:
        print("⚠️  Audio system has missing dependencies")
    print("=" * 60)
    
    return success


if __name__ == "__main__":
    import sys
    import argparse
    
    parser = argparse.ArgumentParser(description="Baby Monitor Audio Analysis")
    parser.add_argument(
        "--test",
        action="store_true",
        help="Test audio system configuration"
    )
    parser.add_argument(
        "--record",
        action="store_true",
        help="Record and analyze audio clip"
    )
    parser.add_argument(
        "--analyze",
        type=str,
        metavar="FILE",
        help="Analyze existing audio file"
    )
    parser.add_argument(
        "--duration",
        type=int,
        default=None,
        help="Recording duration in seconds"
    )
    
    args = parser.parse_args()
    
    # Test mode
    if args.test:
        success = test_audio_system()
        sys.exit(0 if success else 1)
    
    # Analyze file mode
    if args.analyze:
        print(f"\n🔊 Analyzing audio file: {args.analyze}")
        result = analyze_audio_file(args.analyze)
        
        print("\n" + "=" * 60)
        print("ANALYSIS RESULTS")
        print("=" * 60)
        
        if "error" in result:
            print(f"❌ Error: {result['error']}")
        else:
            print(f"Crying detected: {result['is_crying']}")
            print(f"Confidence: {result['confidence']:.2%}")
            print(f"\nFeatures:")
            for key, value in result.get('features', {}).items():
                print(f"  • {key}: {value:.4f}")
        
        print("=" * 60)
        sys.exit(0)
    
    # Record and analyze mode
    if args.record:
        print("\n🎤 Starting audio recording and analysis...")
        result = record_and_analyze()
        
        print("\n" + "=" * 60)
        print("RECORDING AND ANALYSIS RESULTS")
        print("=" * 60)
        
        if "error" in result:
            print(f"❌ Error: {result['error']}")
        else:
            print(f"Audio file: {result.get('audio_file')}")
            print(f"Crying detected: {result['is_crying']}")
            print(f"Confidence: {result['confidence']:.2%}")
        
        print("=" * 60)
        sys.exit(0)
    
    # No arguments - show help
    parser.print_help()

