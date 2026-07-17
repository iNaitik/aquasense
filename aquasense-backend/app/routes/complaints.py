"""Complaint API endpoints."""

from typing import Optional
from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile, status
from pydantic import ValidationError
from sqlalchemy.orm import Session

from app.database import get_db
from app.schemas.complaint import (
    ComplaintDetail,
    CreateComplaintRequest,
    CreateComplaintResponse,
)
from app.services.complaint_service import (
    create_complaint,
    get_complaint_by_reference,
)

router = APIRouter(prefix="/api/v1/complaints", tags=["Complaints"])


@router.post(
    "",
    response_model=CreateComplaintResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Submit a new complaint",
)
def submit_complaint(
    citizen_name: str = Form(...),
    phone_number: str = Form(...),
    issue_type: str = Form(...),
    description: str = Form(...),
    latitude: Optional[float] = Form(None),
    longitude: Optional[float] = Form(None),
    address: Optional[str] = Form(None),
    photo: Optional[UploadFile] = File(None),
    db: Session = Depends(get_db),
) -> CreateComplaintResponse:
    try:
        payload = CreateComplaintRequest(
            citizen_name=citizen_name,
            phone_number=phone_number,
            issue_type=issue_type,
            description=description,
            latitude=latitude,
            longitude=longitude,
            address=address,
        )
    except ValidationError as e:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=e.errors(),
        )
    return create_complaint(db, payload, photo)


@router.get(
    "/{reference_id}",
    response_model=ComplaintDetail,
    summary="Track a complaint by reference ID",
)
def track_complaint(
    reference_id: str,
    db: Session = Depends(get_db),
) -> ComplaintDetail:
    result = get_complaint_by_reference(db, reference_id)
    if result is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Complaint with reference '{reference_id}' not found.",
        )
    return result
