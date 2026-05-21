import os
import datetime
from sqlalchemy import create_engine, Column, String, Integer, DateTime
from sqlalchemy.orm import declarative_base, sessionmaker

DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./docpilot.db")

# For SQLite, ensure threading is handled properly
connect_args = {}
if DATABASE_URL.startswith("sqlite"):
    connect_args["check_same_thread"] = False

engine = create_engine(DATABASE_URL, connect_args=connect_args)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

class Job(Base):
    """
    SQLAlchemy model representing a PDF to Markdown conversion job.
    """
    __tablename__ = "jobs"

    job_id = Column(String, primary_key=True, index=True)
    filename = Column(String, nullable=False)
    status = Column(String, default="queued")  # queued -> parsing -> extracting_images -> describing_images -> writing -> completed | failed
    progress = Column(Integer, default=0)       # 0 - 100
    created_at = Column(DateTime, default=datetime.datetime.utcnow)
    error = Column(String, nullable=True)
    output_path = Column(String, nullable=True)

def init_db():
    """
    Initializes database tables.
    """
    Base.metadata.create_all(bind=engine)

def get_db():
    """
    Dependency to obtain database session context.
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
