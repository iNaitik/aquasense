"""ML model loading and prediction service for pipeline failure risk prototype.

DISCLAIMER:
The pipeline network used in this prototype is simulated and does not represent official
Indore Municipal Corporation infrastructure. The ML model was trained on synthetic historical data.
Risk predictions are prototype demonstration outputs and are not validated assessments of real
Indore water pipelines.
"""

import os
import joblib
import pandas as pd
from typing import Any, Dict

# Exact 8 expected ML input features in strict schema order
EXPECTED_FEATURES = [
    "pipe_age_years",
    "material",
    "diameter_mm",
    "length_m",
    "previous_failures",
    "days_since_last_maintenance",
    "complaints_last_30_days",
    "leakage_complaints_30d",
]

_model_pipeline = None


def get_model_pipeline():
    """Lazily load and cache the trained pipeline failure prediction model (joblib)."""
    global _model_pipeline
    if _model_pipeline is None:
        # Determine path to ml/models/pipeline_failure_model.joblib relative to project root
        project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
        model_path = os.path.join(project_root, "ml", "models", "pipeline_failure_model.joblib")
        if not os.path.exists(model_path):
            raise FileNotFoundError(f"Trained ML model not found at: {model_path}")
        _model_pipeline = joblib.load(model_path)
    return _model_pipeline


def predict_pipeline_risk(features: Dict[str, Any]) -> Dict[str, Any]:
    """Calculate failure probability, risk score, and risk level from raw pipeline features.

    IMPORTANT DISTINCTION:
    The binary classification evaluation threshold (0.65 for Logistic Regression) is used for
    evaluating binary performance on held-out test data. It is NOT the same as the prototype
    map risk-display thresholds below. Map thresholds categorize continuous risk scores:
        - LOW:    risk_score < 40
        - MEDIUM: 40 <= risk_score < 70
        - HIGH:   risk_score >= 70
    """
    # Validate required input feature keys
    for feat in EXPECTED_FEATURES:
        if feat not in features:
            raise ValueError(f"Missing required ML input feature: '{feat}'")

    model = get_model_pipeline()

    # Create single-row DataFrame exactly matching training feature columns
    input_df = pd.DataFrame([{feat: features[feat] for feat in EXPECTED_FEATURES}])

    # Extract positive class probability
    probs = model.predict_proba(input_df)
    failure_probability = float(probs[0, 1])

    # Ensure bounds [0.0, 1.0]
    failure_probability = max(0.0, min(1.0, failure_probability))

    # Calculate risk score [0.0, 100.0]
    risk_score = round(failure_probability * 100.0, 1)

    # Determine risk level based on prototype display thresholds
    if risk_score < 40.0:
        risk_level = "LOW"
    elif risk_score < 70.0:
        risk_level = "MEDIUM"
    else:
        risk_level = "HIGH"

    return {
        "failure_probability": failure_probability,
        "risk_score": risk_score,
        "risk_level": risk_level,
    }
