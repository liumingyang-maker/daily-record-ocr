"""Upload service for managing recognition jobs."""

from fastapi import UploadFile

from app.infrastructure.database.models import RecognitionJob
from app.infrastructure.database.session import get_session
from app.infrastructure.storage.file_storage import save_image
from app.infrastructure.storage.path_manager import generate_job_no


async def create_job(file: UploadFile) -> RecognitionJob:
    dest, filename = await save_image(file)
    job_no = generate_job_no()

    with get_session() as session:
        job = RecognitionJob(
            job_no=job_no,
            source_image_path=str(dest),
            status="UPLOADED",
        )
        session.add(job)
        session.flush()
        session.refresh(job)
        session.expunge(job)
        return job


def list_jobs(limit: int = 50) -> list[RecognitionJob]:
    with get_session() as session:
        jobs = (
            session.query(RecognitionJob)
            .order_by(RecognitionJob.created_at.desc())
            .limit(limit)
            .all()
        )
        for j in jobs:
            session.refresh(j)
            session.expunge(j)
        return jobs


def get_job(job_id: int) -> RecognitionJob | None:
    with get_session() as session:
        job = session.get(RecognitionJob, job_id)
        if job:
            session.refresh(job)
            session.expunge(job)
        return job
