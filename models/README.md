# Models Directory

This directory contains trained machine learning models for the baby monitor system.

## Cry Detector Model

Place your trained cry detection model here as: `cry_detector.joblib`

### Model Requirements:
- Format: Joblib serialized scikit-learn model
- Input: Feature vector with 5 features (from `extract_librosa_features`):
  1. `mfcc_mean` - Mean of MFCC coefficients
  2. `zcr_mean` - Mean zero-crossing rate
  3. `spectral_centroid_mean` - Mean spectral centroid
  4. `rms_mean` - Mean RMS energy
  5. `tempo` - Estimated tempo
- Output: Binary classification (0 = no cry, 1 = cry)
- Recommended: Model should have `predict_proba()` method for confidence scores

### Training Your Own Model

You can train your own cry detector using scikit-learn:

```python
from sklearn.ensemble import RandomForestClassifier
import joblib

# Train your model
model = RandomForestClassifier(n_estimators=100)
model.fit(X_train, y_train)

# Save the model
joblib.dump(model, 'models/cry_detector.joblib')
```

### Using Without a Model

If no model is present, the system will:
- Return `is_crying: False` with `confidence: 0.0`
- Log a warning message
- Continue operating normally (vision-only monitoring)

