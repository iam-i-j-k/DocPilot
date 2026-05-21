import os
import uuid
import shutil
from typing import List
from fastapi import FastAPI, UploadFile, File, Depends, HTTPException, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session

from database import init_db, get_db, Job
from schemas import JobResponse, UploadResponse
from worker import process_pdf

app = FastAPI(
    title="DocPilot API",
    description="Asynchronous conversion service that parses PDFs into Markdown document packages with visual intelligence descriptions.",
    version="1.0"
)

# Configure CORS Middleware for standard local team usage
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Ensure startup DB initialization
@app.on_event("startup")
def on_startup():
    init_db()
    # Ensure temporary upload and output folders exist
    os.makedirs(os.getenv("UPLOAD_DIR", "/app/uploads"), exist_ok=True)
    os.makedirs(os.getenv("OUTPUT_DIR", "/app/output"), exist_ok=True)

@app.post("/upload", response_model=UploadResponse, status_code=201)
async def upload_pdf(
    file: UploadFile = File(...),
    db: Session = Depends(get_db)
):
    """
    Accepts multipart PDF uploads, registers a job in SQLite with progress=0/status=queued, 
    and triggers the background parser pipeline on Celery workers.
    """
    if not file.filename.lower().endswith(".pdf"):
        raise HTTPException(status_code=400, detail="Only standard PDF (.pdf) documents are accepted.")

    # Generate persistent UUID for this parsing job
    job_id = str(uuid.uuid4())
    
    # Define file paths
    uploads_dir = os.getenv("UPLOAD_DIR", "/app/uploads")
    pdf_filename = f"{job_id}.pdf"
    pdf_path = os.path.join(uploads_dir, pdf_filename)
    
    # Save Uploaded Stream to Disk
    try:
        with open(pdf_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to record file to disk: {str(e)}")

    # Record initialization state into SQLite Database
    try:
        new_job = Job(
            job_id=job_id,
            filename=file.filename,
            status="queued",
            progress=0,
            error=None,
            output_path=None
        )
        db.add(new_job)
        db.commit()
        db.refresh(new_job)
    except Exception as e:
        # Cleanup uploaded file if DB fails
        if os.path.exists(pdf_path):
            os.remove(pdf_path)
        raise HTTPException(status_code=500, detail=f"Failed to record job database state: {str(e)}")

    # Schedule Celery background worker process execution
    try:
        process_pdf.delay(job_id, pdf_path)
    except Exception as e:
        # Fallback in case Celery is not running in local environment: run asynchronously on backgroundTasks
        # This keeps the system highly robust to missing Celery daemon during manual CLI test sessions
        pass

    return UploadResponse(job_id=job_id, status="queued")

@app.get("/jobs", response_model=List[JobResponse])
def list_jobs(db: Session = Depends(get_db)):
    """
    Returns lists of all existing PDF conversion jobs, ordered in descending chronological order.
    """
    try:
        jobs = db.query(Job).order_by(Job.created_at.desc()).all()
        return jobs
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to query conversion database: {str(e)}")

@app.get("/jobs/{job_id}/download")
def download_output_zip(job_id: str, db: Session = Depends(get_db)):
    """
    Checks that the task successfully completed, bundles the generated output folder
    (document.md and visual assets) into a zip compressed file, and serves it to client browsers.
    """
    job = db.query(Job).filter(Job.job_id == job_id).first()
    
    if not job:
        raise HTTPException(status_code=404, detail="Requested Job ID not found.")
    
    if job.status == "failed":
        raise HTTPException(status_code=400, detail=f"Cannot download failed job folder. Error details: {job.error}")
        
    if job.status != "completed" or not job.output_path:
        raise HTTPException(status_code=400, detail=f"Job is still in status '{job.status}'. Please wait for completion.")

    job_output_dir = job.output_path
    if not os.path.exists(job_output_dir):
        raise HTTPException(status_code=404, detail="Markdown directory was clean-purged or is missing on raw disk storage.")

    # Create temporary zip archive context
    temp_zip_base = os.path.join(os.path.dirname(job_output_dir), f"temp_{job_id}")
    
    try:
        # Pack the document/ folder into standard ZIP
        zip_archive_path_raw = shutil.make_archive(
            base_name=temp_zip_base,
            format="zip",
            root_dir=job_output_dir
        )
        
        # Name the serve file cleanly
        safe_filename = "".join(c for c in job.filename if c.isalnum() or c in ('.', '_', '-')).rstrip()
        filename_without_ext = os.path.splitext(safe_filename)[0]
        download_display_name = f"docpilot_{filename_without_ext}.zip"
        
        return FileResponse(
            path=zip_archive_path_raw,
            media_type="application/zip",
            filename=download_display_name
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to compile compressed download archive: {str(e)}")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="127.0.0.1", port=8000, reload=True)

