"""Pipeline risk recalculation service combining baseline and dynamic citizen complaints."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from sqlalchemy.orm import Session

from app.models.complaint import Complaint, IssueType
from app.models.pipeline import Pipeline
from app.services.pipeline_prediction_service import predict_pipeline_risk


def recalculate_pipeline_risk_from_complaints(db: Session, pipeline: Pipeline) -> Pipeline:
    """Recalculate rolling 30-day complaint counts and update ML failure risk for a pipeline.

    Calculates:
      - effective_complaints_last_30_days = baseline + real matched complaints within last 30 days
      - effective_leakage_complaints_30d  = baseline + real matched water_leakage complaints within last 30 days
    And calls the existing ML prediction service to update failure_probability, risk_score, and risk_level.
    """
    cutoff = datetime.now(timezone.utc) - timedelta(days=30)

    # 1. Calculate real matched complaints in the last 30 days (all issue types)
    real_matched_complaints = (
        db.query(Complaint)
        .filter(
            Complaint.matched_pipeline_id == pipeline.id,
            Complaint.created_at >= cutoff,
        )
        .count()
    )

    # 2. Calculate real matched water_leakage complaints in the last 30 days
    real_matched_leakage = (
        db.query(Complaint)
        .filter(
            Complaint.matched_pipeline_id == pipeline.id,
            Complaint.created_at >= cutoff,
            Complaint.issue_type == IssueType.water_leakage,
        )
        .count()
    )

    # 3. Add synthetic baseline values (Section 7)
    effective_complaints = pipeline.baseline_complaints_30d + real_matched_complaints
    effective_leakage = pipeline.baseline_leakage_complaints_30d + real_matched_leakage

    # 4. Update effective counts on the pipeline record
    pipeline.complaints_last_30_days = effective_complaints
    pipeline.leakage_complaints_30d = effective_leakage

    # 5. Prepare exact 8 features for ML prediction
    features = {
        "pipe_age_years": pipeline.pipe_age_years,
        "material": pipeline.material,
        "diameter_mm": pipeline.diameter_mm,
        "length_m": pipeline.length_m,
        "previous_failures": pipeline.previous_failures,
        "days_since_last_maintenance": pipeline.days_since_last_maintenance,
        "complaints_last_30_days": pipeline.complaints_last_30_days,
        "leakage_complaints_30d": pipeline.leakage_complaints_30d,
    }

    # 6. Run ML prediction using existing service
    prediction = predict_pipeline_risk(features)

    # 7. Update risk values on pipeline record
    pipeline.failure_probability = prediction["failure_probability"]
    pipeline.risk_score = prediction["risk_score"]
    pipeline.risk_level = prediction["risk_level"]

    return pipeline
