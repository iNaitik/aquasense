"""Pipeline ORM model for AQUA-SENSE simulated network segments."""

from sqlalchemy import (
    Column,
    DateTime,
    Float,
    Integer,
    String,
    func,
)

from app.database import Base


class Pipeline(Base):
    """Pipeline ORM model representing simulated water network segments and risk assessments.
    
    DISCLAIMER:
    The pipeline network used in this prototype is simulated and does not represent official
    Indore Municipal Corporation infrastructure. The ML model was trained on synthetic historical data.
    Risk predictions are prototype demonstration outputs and are not validated assessments of real
    Indore water pipelines.
    """
    __tablename__ = "pipelines"

    id = Column(Integer, primary_key=True, autoincrement=True)
    pipeline_id = Column(String(50), unique=True, nullable=False, index=True)

    start_latitude = Column(Float, nullable=False)
    start_longitude = Column(Float, nullable=False)
    end_latitude = Column(Float, nullable=False)
    end_longitude = Column(Float, nullable=False)
    center_latitude = Column(Float, nullable=False)
    center_longitude = Column(Float, nullable=False)

    pipe_age_years = Column(Float, nullable=False)
    material = Column(String(50), nullable=False)
    diameter_mm = Column(Float, nullable=False)
    length_m = Column(Float, nullable=False)

    previous_failures = Column(Integer, nullable=False)
    days_since_last_maintenance = Column(Float, nullable=False)

    baseline_complaints_30d = Column(Integer, nullable=False, default=0)
    baseline_leakage_complaints_30d = Column(Integer, nullable=False, default=0)
    complaints_last_30_days = Column(Integer, nullable=False)
    leakage_complaints_30d = Column(Integer, nullable=False)

    failure_probability = Column(Float, nullable=False)
    risk_score = Column(Float, nullable=False)
    risk_level = Column(String(20), nullable=False, index=True)  # LOW, MEDIUM, HIGH

    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )
