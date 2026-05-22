"""
DocPilot API — main.py
Asynchronous PDF → Markdown conversion service with visual intelligence descriptions.

Fixes applied vs original:
  1. Celery failure no longer silently swallowed — falls back to FastAPI BackgroundTasks
  2. Temp zip file cleaned up after FileResponse via BackgroundTasks
  3. Added GET /jobs/{job_id}/status endpoint for polling
  4. Fixed CORS: allow_credentials=True is incompatible with allow_origins=["*"]
  5. Replaced deprecated @app.on_event("startup") with lifespan context manager
  6. Added pagination (skip/limit) to GET /jobs
  7. Fixed safe_filename to handle unicode and edge cases properly
"""

import os
import uuid
import shutil
from contextlib import asynccontextmanager
from typing import List

from fastapi import BackgroundTasks, Depends, FastAPI, File, HTTPException, Query, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session

from database import Job, get_db, init_db
from schemas import JobResponse, JobStatusResponse, UploadResponse
from worker import process_pdf


# ─── Lifespan (replaces deprecated @app.on_event) ────────────────────────────

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Runs once on startup before the server begins accepting requests."""
    init_db()
    os.makedirs(os.getenv("UPLOAD_DIR", "/app/uploads"), exist_ok=True)
    os.makedirs(os.getenv("OUTPUT_DIR", "/app/output"), exist_ok=True)
    yield
    # Nothing to teardown currently; add cleanup here if needed


# ─── App ──────────────────────────────────────────────────────────────────────

app = FastAPI(
    title="DocPilot API",
    description=(
        "Asynchronous conversion service that parses PDFs into Markdown document "
        "packages with visual intelligence descriptions."
    ),
    version="1.0",
    lifespan=lifespan,
)

# FIX: allow_credentials=True is spec-invalid with allow_origins=["*"].
# Browsers reject preflight responses with that combination.
# Option A (development): drop credentials, keep wildcard.
# Option B (production): restrict origins, keep credentials.
# Using Option A here; swap to Option B before any real deployment.
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,   # was True — invalid with wildcard origin
    allow_methods=["*"],
    allow_headers=["*"],
)


# ─── Helpers ──────────────────────────────────────────────────────────────────

def _safe_filename(raw: str) -> str:
    """
    Sanitizes a filename for use in Content-Disposition headers.
    Handles unicode, spaces, and special characters robustly.
    """
    # Normalize unicode to ASCII where possible, drop the rest
    import unicodedata
    normalized = unicodedata.normalize("NFKD", raw)
    ascii_name = normalized.encode("ascii", "ignore").decode("ascii")
    # Keep only safe characters
    safe = "".join(c for c in ascii_name if c.isalnum() or c in (".", "_", "-", " "))
    safe = safe.strip().replace(" ", "_")
    return safe or "document"


def _cleanup_file(path: str) -> None:
    """Silently removes a file; used as a background cleanup task."""
    try:
        if os.path.exists(path):
            os.remove(path)
    except Exception as exc:
        # Non-fatal: log but don't raise
        print(f"[cleanup] Warning: could not delete {path}: {exc}")


def _run_process_pdf_sync(job_id: str, pdf_path: str) -> None:
    """
    Direct (non-Celery) fallback for process_pdf.
    Calls the same worker function synchronously inside a BackgroundTask.
    Import the underlying function, not the Celery task wrapper.
    """
    from worker import process_pdf_sync  # define this in worker.py as the plain function
    process_pdf_sync(job_id, pdf_path)


# ─── Routes ───────────────────────────────────────────────────────────────────

@app.post("/upload", response_model=UploadResponse, status_code=201)
async def upload_pdf(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
):
    """
    Accepts multipart PDF uploads, registers a job in SQLite with
    status=queued, and dispatches to Celery. Falls back to FastAPI
    BackgroundTasks if Celery is unavailable.
    """
    if not file.filename.lower().endswith(".pdf"):
        raise HTTPException(
            status_code=400,
            detail="Only standard PDF (.pdf) documents are accepted.",
        )

    job_id = str(uuid.uuid4())
    uploads_dir = os.getenv("UPLOAD_DIR", "/app/uploads")
    pdf_path = os.path.join(uploads_dir, f"{job_id}.pdf")

    # Save upload to disk
    try:
        with open(pdf_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
    except Exception as exc:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to write file to disk: {exc}",
        )

    # Register job in DB
    try:
        new_job = Job(
            job_id=job_id,
            filename=file.filename,
            status="queued",
            progress=0,
            error=None,
            output_path=None,
        )
        db.add(new_job)
        db.commit()
        db.refresh(new_job)
    except Exception as exc:
        _cleanup_file(pdf_path)
        raise HTTPException(
            status_code=500,
            detail=f"Failed to register job in database: {exc}",
        )

    # Dispatch to Celery; fall back to BackgroundTasks if broker is unreachable
    celery_dispatched = False
    try:
        process_pdf.delay(job_id, pdf_path)
        celery_dispatched = True
    except Exception as exc:
        print(f"[upload] Celery unavailable ({exc}). Falling back to BackgroundTasks.")

    if not celery_dispatched:
        # FIX: actually run the task instead of silently dropping it
        background_tasks.add_task(_run_process_pdf_sync, job_id, pdf_path)

    return UploadResponse(job_id=job_id, status="queued")


@app.get("/jobs", response_model=List[JobResponse])
def list_jobs(
    skip: int = Query(default=0, ge=0, description="Number of records to skip"),
    limit: int = Query(default=50, ge=1, le=500, description="Max records to return"),
    db: Session = Depends(get_db),
):
    """
    Returns all PDF conversion jobs in descending chronological order.
    Supports pagination via skip/limit query params.
    """
    jobs = db.query(Job).order_by(Job.created_at.desc()).offset(skip).limit(limit).all()
    return jobs


@app.get("/jobs/{job_id}/status", response_model=JobStatusResponse)
def get_job_status(job_id: str, db: Session = Depends(get_db)):
    """
    Returns the current status and progress of a single job.
    Use this to poll for completion instead of fetching the full jobs list.
    """
    job = db.query(Job).filter(Job.job_id == job_id).first()
    if not job:
        raise HTTPException(status_code=404, detail="Job ID not found.")
    return job


@app.get("/jobs/{job_id}/download")
def download_output_zip(
    job_id: str,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
):
    """
    Bundles the completed job's output folder into a zip and streams it.
    The temporary zip is deleted after the response is sent.
    """
    job = db.query(Job).filter(Job.job_id == job_id).first()

    if not job:
        raise HTTPException(status_code=404, detail="Job ID not found.")

    if job.status == "failed":
        raise HTTPException(
            status_code=400,
            detail=f"Cannot download a failed job. Error: {job.error}",
        )

    if job.status != "completed" or not job.output_path:
        raise HTTPException(
            status_code=400,
            detail=f"Job is not ready for download (current status: '{job.status}').",
        )

    if not os.path.exists(job.output_path):
        raise HTTPException(
            status_code=404,
            detail="Output directory missing from disk. It may have been purged.",
        )

    temp_zip_base = os.path.join(
        os.path.dirname(job.output_path), f"temp_{job_id}"
    )

    try:
        zip_path = shutil.make_archive(
            base_name=temp_zip_base,
            format="zip",
            root_dir=job.output_path,
        )
    except Exception as exc:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to create zip archive: {exc}",
        )

    # FIX: schedule temp zip deletion after the response is fully sent
    background_tasks.add_task(_cleanup_file, zip_path)

    safe_stem = os.path.splitext(_safe_filename(job.filename))[0]
    download_name = f"docpilot_{safe_stem}.zip"

    return FileResponse(
        path=zip_path,
        media_type="application/zip",
        filename=download_name,
        background=background_tasks,
    )


@app.post("/jobs/{job_id}/cancel", status_code=200)
def cancel_job(job_id: str, db: Session = Depends(get_db)):
    """
    Cancels a queued or processing job, removes it from the database,
    and cleans up all associated files on disk.
    """
    job = db.query(Job).filter(Job.job_id == job_id).first()

    if not job:
        raise HTTPException(status_code=404, detail="Job ID not found.")

    if job.status in ("completed", "failed"):
        raise HTTPException(
            status_code=400,
            detail=f"Cannot cancel a job that is already '{job.status}'.",
        )

    # Clean up uploaded PDF
    uploads_dir = os.getenv("UPLOAD_DIR", "/app/uploads")
    _cleanup_file(os.path.join(uploads_dir, f"{job_id}.pdf"))

    # Clean up output directory
    if job.output_path and os.path.exists(job.output_path):
        try:
            shutil.rmtree(job.output_path)
        except Exception as exc:
            print(f"[cancel] Warning: could not delete output dir {job.output_path}: {exc}")

    # Remove DB record
    try:
        db.delete(job)
        db.commit()
    except Exception as exc:
        db.rollback()
        raise HTTPException(
            status_code=500,
            detail=f"Failed to remove job from database: {exc}",
        )

    return {"status": "cancelled", "message": f"Job {job_id} cancelled and removed."}


# ─── Dev entrypoint ───────────────────────────────────────────────────────────

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="127.0.0.1", port=8000, reload=True)