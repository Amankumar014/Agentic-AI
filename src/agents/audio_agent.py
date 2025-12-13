"""
Audio analysis agent for real-time baby monitoring.

Provides audio analysis including crying detection, awakening detection,
sound classification, and noise level monitoring.
"""
import logging
import time
from typing import Dict, Any, Optional
import numpy as np
from pathlib import Path

logger = logging.getLogger(__name__)


class AudioAnalyzer:
    """
    Audio analysis agent for baby monitoring.
    
    Analyzes audio chunks to detect:
    - Crying
    - Awakening (sudden sound after silence)
    - Sound classification (crying vs laughing vs normal)
    - Other voices detection
    - Noise levels
    - Silence periods
    """
    
    def __init__(self):
        """Initialize audio analyzer."""
        self._initialized = False
        self._librosa_available = False
        self._cry_model = None
        self._model_loaded = False
        
        # Silence tracking
        self._last_noise_time = time.time()
        self._silence_duration = 0.0
        self._last_rms = 0.0
        
        # Initialize on first use
        logger.info("AudioAnalyzer created (lazy initialization)")
    
    def _lazy_init(self):
        """Lazy initialization of audio libraries and models."""
        if self._initialized:
            return
        
        try:
            import librosa
            self._librosa_available = True
            logger.info("✅ librosa available for audio analysis")
        except ImportError:
            logger.warning("⚠️ librosa not available - audio analysis will be limited")
            self._librosa_available = False
        
        # Try to load cry detection model
        try:
            import joblib
            project_root = Path(__file__).parent.parent.parent
            model_path = project_root / "models" / "cry_detector.joblib"
            
            if model_path.exists():
                self._cry_model = joblib.load(model_path)
                self._model_loaded = True
                logger.info(f"✅ Cry detector model loaded from {model_path}")
            else:
                logger.info(f"ℹ️ Cry detector model not found at {model_path}")
        except Exception as e:
            logger.warning(f"⚠️ Could not load cry detector model: {e}")
        
        self._initialized = True
    
    def analyze(self, audio_chunk: np.ndarray, sample_rate: int) -> Dict[str, Any]:
        """
        Analyze audio chunk and return detection results.
        
        Args:
            audio_chunk: Audio samples as numpy array (float32, mono)
            sample_rate: Sample rate in Hz
        
        Returns:
            Dict with audio analysis results:
            {
                "audio_detected": bool,
                "noise_level": float,  # dB
                "rms_energy": float,
                "sound_type": str,  # "crying", "laughing", "normal", "other_voice", "silence"
                "is_crying": bool,
                "crying_confidence": float,
                "is_awakening": bool,
                "other_voice_detected": bool,
                "silence_duration": float,  # seconds
                "features": dict,  # librosa features if available
                "analysis_available": bool
            }
        """
        self._lazy_init()
        
        if audio_chunk is None or len(audio_chunk) == 0:
            return self._empty_result("No audio data")
        
        try:
            # Calculate basic audio metrics
            rms = self._calculate_rms(audio_chunk)
            db_level = self._rms_to_db(rms)
            
            # Check for silence
            from src.config import get_settings
            settings = get_settings()
            silence_threshold = settings.AUDIO_SILENCE_THRESHOLD
            
            is_silent = rms < silence_threshold
            
            # Update silence tracking
            if is_silent:
                self._silence_duration = time.time() - self._last_noise_time
            else:
                self._last_noise_time = time.time()
                self._silence_duration = 0.0
            
            # Check for awakening (sudden sound after silence)
            awakening_threshold = settings.AUDIO_AWAKENING_THRESHOLD
            is_awakening = (
                self._silence_duration > 2.0 and  # Was silent for 2+ seconds
                rms > awakening_threshold and  # Sudden increase in volume
                rms > self._last_rms * 3.0  # 3x increase from previous
            )
            
            self._last_rms = rms
            
            # Extract features if librosa available
            features = {}
            if self._librosa_available and not is_silent:
                features = self._extract_features(audio_chunk, sample_rate)
            
            # Classify sound type
            sound_type = "silence" if is_silent else "normal"
            is_crying = False
            crying_confidence = 0.0
            other_voice_detected = False
            
            if not is_silent and features:
                # Classify cry using model if available
                if self._model_loaded and self._cry_model is not None:
                    cry_result = self._classify_cry(features)
                    is_crying = cry_result["is_crying"]
                    crying_confidence = cry_result["confidence"]
                else:
                    # Fallback: simple heuristic cry detection
                    cry_result = self._simple_cry_detection(features)
                    is_crying = cry_result["is_crying"]
                    crying_confidence = cry_result["confidence"]
                
                # Detect other voice (adult voice characteristics)
                other_voice_detected = self._detect_other_voice(features)
                
                # Determine sound type
                if is_crying:
                    sound_type = "crying"
                elif other_voice_detected:
                    sound_type = "other_voice"
                elif self._is_laughing(features):
                    sound_type = "laughing"
                else:
                    sound_type = "normal"
            
            result = {
                "audio_detected": not is_silent,
                "noise_level": float(db_level),
                "rms_energy": float(rms),
                "sound_type": sound_type,
                "is_crying": is_crying,
                "crying_confidence": float(crying_confidence),
                "is_awakening": is_awakening,
                "other_voice_detected": other_voice_detected,
                "silence_duration": float(self._silence_duration),
                "features": features,
                "analysis_available": True,
                "librosa_available": self._librosa_available,
                "model_loaded": self._model_loaded
            }
            
            return result
        
        except Exception as e:
            logger.error(f"Error analyzing audio: {e}", exc_info=True)
            return self._empty_result(f"Error: {str(e)}")
    
    def _calculate_rms(self, audio: np.ndarray) -> float:
        """Calculate RMS (root-mean-square) energy of audio."""
        return float(np.sqrt(np.mean(audio ** 2)))
    
    def _rms_to_db(self, rms: float, reference: float = 1.0) -> float:
        """Convert RMS to decibels."""
        if rms < 1e-10:
            return -100.0  # Very quiet
        return float(20 * np.log10(rms / reference))
    
    def _extract_features(self, audio: np.ndarray, sample_rate: int) -> Dict[str, float]:
        """
        Extract audio features using librosa.
        
        Args:
            audio: Audio samples
            sample_rate: Sample rate in Hz
        
        Returns:
            Dict with features: mfcc_mean, zcr_mean, spectral_centroid_mean, rms_mean, tempo
        """
        if not self._librosa_available:
            return {}
        
        try:
            import librosa
            import warnings
            
            with warnings.catch_warnings():
                warnings.simplefilter("ignore")
                
                # MFCC (Mel-frequency cepstral coefficients)
                mfccs = librosa.feature.mfcc(y=audio, sr=sample_rate, n_mfcc=13)
                mfcc_mean = float(np.mean(mfccs))
                
                # Zero-crossing rate (voice activity, pitch)
                zcr = librosa.feature.zero_crossing_rate(audio)
                zcr_mean = float(np.mean(zcr))
                
                # Spectral centroid (brightness of sound)
                spectral_centroids = librosa.feature.spectral_centroid(y=audio, sr=sample_rate)
                spectral_centroid_mean = float(np.mean(spectral_centroids))
                
                # RMS energy
                rms = librosa.feature.rms(y=audio)
                rms_mean = float(np.mean(rms))
                
                # Tempo estimation
                try:
                    tempo, _ = librosa.beat.beat_track(y=audio, sr=sample_rate)
                    tempo = float(tempo) if tempo else 0.0
                except Exception:
                    tempo = 0.0
                
                # Spectral rolloff (frequency below which 85% of energy is contained)
                rolloff = librosa.feature.spectral_rolloff(y=audio, sr=sample_rate)
                rolloff_mean = float(np.mean(rolloff))
                
                return {
                    "mfcc_mean": mfcc_mean,
                    "zcr_mean": zcr_mean,
                    "spectral_centroid_mean": spectral_centroid_mean,
                    "rms_mean": rms_mean,
                    "tempo": tempo,
                    "spectral_rolloff_mean": rolloff_mean
                }
        
        except Exception as e:
            logger.error(f"Error extracting audio features: {e}")
            return {}
    
    def _classify_cry(self, features: Dict[str, float]) -> Dict[str, Any]:
        """
        Classify audio as crying using trained model.
        
        Args:
            features: Audio features dict
        
        Returns:
            Dict with is_crying (bool) and confidence (float)
        """
        if not self._model_loaded or self._cry_model is None:
            return {"is_crying": False, "confidence": 0.0}
        
        try:
            # Convert features to vector (consistent order)
            feature_names = [
                "mfcc_mean",
                "zcr_mean",
                "spectral_centroid_mean",
                "rms_mean",
                "tempo"
            ]
            
            feature_vector = np.array([
                features.get(name, 0.0) for name in feature_names
            ]).reshape(1, -1)
            
            # Make prediction
            prediction = self._cry_model.predict(feature_vector)[0]
            
            # Get confidence if available
            confidence = 0.5
            if hasattr(self._cry_model, 'predict_proba'):
                proba = self._cry_model.predict_proba(feature_vector)[0]
                confidence = float(proba[1] if len(proba) > 1 else proba[0])
            
            return {
                "is_crying": bool(prediction),
                "confidence": confidence
            }
        
        except Exception as e:
            logger.error(f"Error in cry classification: {e}")
            return {"is_crying": False, "confidence": 0.0}
    
    def _simple_cry_detection(self, features: Dict[str, float]) -> Dict[str, Any]:
        """
        Simple heuristic-based cry detection (fallback when no model).
        
        Baby crying characteristics:
        - High zero-crossing rate (ZCR > 0.15)
        - High RMS energy (> 0.05)
        - Specific frequency range (high spectral centroid > 2000 Hz)
        """
        zcr = features.get("zcr_mean", 0.0)
        rms = features.get("rms_mean", 0.0)
        centroid = features.get("spectral_centroid_mean", 0.0)
        
        # Crying indicators
        high_zcr = zcr > 0.15
        high_rms = rms > 0.05
        high_pitch = centroid > 2000.0
        
        # Count indicators
        indicators = sum([high_zcr, high_rms, high_pitch])
        
        # Need at least 2 indicators for crying
        is_crying = indicators >= 2
        confidence = indicators / 3.0  # 0.0 to 1.0
        
        return {
            "is_crying": is_crying,
            "confidence": confidence
        }
    
    def _detect_other_voice(self, features: Dict[str, float]) -> bool:
        """
        Detect if audio contains adult voice (vs baby).
        
        Adult voice characteristics:
        - Lower frequency (spectral centroid < 1500 Hz)
        - Lower zero-crossing rate
        """
        centroid = features.get("spectral_centroid_mean", 0.0)
        zcr = features.get("zcr_mean", 0.0)
        
        # Adult voice has lower frequencies
        low_pitch = centroid < 1500.0
        low_zcr = zcr < 0.1
        
        return low_pitch and low_zcr
    
    def _is_laughing(self, features: Dict[str, float]) -> bool:
        """
        Detect laughing sounds.
        
        Laughing characteristics:
        - Rhythmic pattern (tempo > 0)
        - Moderate-high energy
        - Moderate zero-crossing rate
        """
        tempo = features.get("tempo", 0.0)
        rms = features.get("rms_mean", 0.0)
        zcr = features.get("zcr_mean", 0.0)
        
        # Laughing indicators
        rhythmic = tempo > 80.0
        moderate_energy = 0.03 < rms < 0.15
        moderate_zcr = 0.08 < zcr < 0.15
        
        return rhythmic and moderate_energy and moderate_zcr
    
    def _empty_result(self, reason: str = "No data") -> Dict[str, Any]:
        """Return empty result structure."""
        return {
            "audio_detected": False,
            "noise_level": -100.0,
            "rms_energy": 0.0,
            "sound_type": "silence",
            "is_crying": False,
            "crying_confidence": 0.0,
            "is_awakening": False,
            "other_voice_detected": False,
            "silence_duration": 0.0,
            "features": {},
            "analysis_available": False,
            "reason": reason
        }


# Global audio analyzer instance
_audio_analyzer: Optional[AudioAnalyzer] = None


def get_audio_analyzer() -> AudioAnalyzer:
    """
    Get or create the global audio analyzer instance.
    
    Returns:
        AudioAnalyzer: The global audio analyzer
    """
    global _audio_analyzer
    
    if _audio_analyzer is None:
        _audio_analyzer = AudioAnalyzer()
    
    return _audio_analyzer
