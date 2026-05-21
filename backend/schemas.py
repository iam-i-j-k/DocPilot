from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime

class JobResponse(BaseModel):
    """
    Pydantic schema representing the serialized output of a conversion job.
    """
    job_id: str
    filename: str
    status: str
    progress: int
    created_at: datetime
    error: Optional[str] = None
    output_path: Optional[str] = None

    class Config:
        from_attributes = True

class UploadResponse(BaseModel):
    """
    Response schema for a successful upload of a PDF files.
    """
    job_id: str
    status: str
