"""Pipeline API endpoints for simulated Indore network map and risk inspection.

DISCLAIMER:
The pipeline network used in this prototype is simulated and does not represent official
Indore Municipal Corporation infrastructure. The ML model was trained on synthetic historical data.
Risk predictions are prototype demonstration outputs and are not validated assessments of real
Indore water pipelines.
"""

from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.database import get_db
from app.core.security import get_current_authority
from app.models.pipeline import Pipeline
from app.schemas.pipeline import PipelineDetail, PipelineMapItem, PipelineStatsSummary

router = APIRouter(
    prefix="/api/v1/pipelines",
    tags=["Pipelines"],
    dependencies=[Depends(get_current_authority)],
)


@router.get(
    "/stats/summary",
    response_model=PipelineStatsSummary,
    summary="Get aggregate summary statistics for the Indore pipeline network",
    description=(
        "Returns total pipeline count, risk level distribution (LOW, MEDIUM, HIGH), "
        "and average risk score calculated dynamically from the database. \n\n"
        "DISCLAIMER: This network is simulated for prototype demonstration only."
    ),
)
def get_pipeline_summary_stats(db: Session = Depends(get_db)) -> PipelineStatsSummary:
    """Get dynamic summary statistics for all simulated pipeline segments in the database."""
    total = db.query(func.count(Pipeline.id)).scalar() or 0

    risk_counts_query = (
        db.query(Pipeline.risk_level, func.count(Pipeline.id))
        .group_by(Pipeline.risk_level)
        .all()
    )
    risk_distribution = {"LOW": 0, "MEDIUM": 0, "HIGH": 0}
    for level, count in risk_counts_query:
        if level in risk_distribution:
            risk_distribution[level] = count
        else:
            risk_distribution[str(level)] = count

    avg_score = db.query(func.avg(Pipeline.risk_score)).scalar() or 0.0

    return PipelineStatsSummary(
        total_pipelines=total,
        risk_distribution=risk_distribution,
        average_risk_score=round(float(avg_score), 2),
    )


@router.get(
    "",
    response_model=List[PipelineMapItem],
    summary="Get lightweight pipeline segments for the government risk map",
    description=(
        "Returns geographic coordinates and risk scores required for rendering the map view. "
        "Supports optional filtering by risk_level (`LOW`, `MEDIUM`, `HIGH`).\n\n"
        "DISCLAIMER: Simulated network for prototype demonstration only."
    ),
)
def get_pipelines(
    risk_level: Optional[str] = Query(
        None,
        description="Filter pipeline segments by risk level: LOW, MEDIUM, or HIGH",
    ),
    db: Session = Depends(get_db),
) -> List[PipelineMapItem]:
    """Get lightweight pipeline list suitable for direct frontend map rendering."""
    query = db.query(Pipeline)
    if risk_level is not None:
        level_upper = risk_level.strip().upper()
        if level_upper not in {"LOW", "MEDIUM", "HIGH"}:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid risk_level filter. Must be LOW, MEDIUM, or HIGH.",
            )
        query = query.filter(Pipeline.risk_level == level_upper)

    # Order by pipeline_id for consistent results
    pipelines = query.order_by(Pipeline.pipeline_id).all()
    return pipelines


@router.get(
    "/{pipeline_id}",
    response_model=PipelineDetail,
    summary="Get detailed information for a specific pipeline segment",
    description=(
        "Returns full infrastructure attributes, complaint counts, failure probability, "
        "and risk score for the specified `pipeline_id`.\n\n"
        "DISCLAIMER: Simulated network for prototype demonstration only."
    ),
)
def get_pipeline_detail(
    pipeline_id: str, db: Session = Depends(get_db)
) -> PipelineDetail:
    """Get complete attribute details for an individual pipeline segment."""
    pipeline = db.query(Pipeline).filter(Pipeline.pipeline_id == pipeline_id).first()
    if not pipeline:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Pipeline '{pipeline_id}' not found",
        )
    return pipeline
