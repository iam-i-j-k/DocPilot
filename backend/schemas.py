"""
DocPilot API — schemas.py
Pydantic response models for all API endpoints.
"""

from datetime import datetime
from typing import Optional

from pydantic import BaseModel


class UploadResponse(BaseModel):
    job_id: str
    status: str


class JobStatusResponse(BaseModel):
    """Lightweight model for /jobs/{job_id}/status polling."""
    job_id: str
    status: str
    progress: int
    error: Optional[str] = None

    class Config:
        from_attributes = True


class JobResponse(BaseModel):
    """Full job record returned by GET /jobs."""
    job_id: str
    filename: str
    status: str
    progress: int
    error: Optional[str] = None
    output_path: Optional[str] = None
    created_at: datetime

    class Config:
        from_attributes = True