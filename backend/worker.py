import os
import logging
from celery import Celery
from database import SessionLocal, Job
from engine.pipeline import Pipeline

# Read system configurations
REDIS_URL = os.getenv("REDIS_URL", "redis://redis:6379/0")
OUTPUT_DIR = os.getenv("OUTPUT_DIR", "/app/output")

# Configure celery
celery_app = Celery("docpilot", broker=REDIS_URL, backend=REDIS_URL)

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("docpilot.celery_worker")


def process_pdf_sync(job_id: str, pdf_path: str):
    """
    Shared synchronous implementation used by BOTH:
    - Celery async worker
    - FastAPI BackgroundTasks fallback
    """

    logger.info(f"Triggered conversion task for Job UUID: {job_id}, Reading: {pdf_path}")

    db = SessionLocal()

    try:
        Pipeline.run(
            pdf_path=pdf_path,
            job_id=job_id,
            output_base_dir=OUTPUT_DIR
        )

        logger.info(f"Successfully processed PDF for Job: {job_id}")

    except Exception as exc:
        logger.error(
            f"Failed to process Job: {job_id}. Reason: {str(exc)}",
            exc_info=True
        )

        try:
            job = db.query(Job).filter(Job.job_id == job_id).first()

            if job:
                job.status = "failed"
                job.error = str(exc)
                db.commit()

        except Exception as db_err:
            logger.error(
                f"Could not write failed status to DB: {str(db_err)}"
            )

    finally:
        db.close()


@celery_app.task(name="process_pdf")
def process_pdf(job_id: str, pdf_path: str):
    """
    Celery wrapper task.
    """
    return process_pdf_sync(job_id, pdf_path)