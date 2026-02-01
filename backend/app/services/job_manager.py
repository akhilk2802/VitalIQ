"""
Simple in-memory job manager for async background tasks.

For production, consider using Redis or a database for persistence.
"""

from typing import Dict, Any, Optional
from datetime import datetime
from enum import Enum
import uuid
import asyncio
from dataclasses import dataclass, field


class JobStatus(str, Enum):
    pending = "pending"
    running = "running"
    completed = "completed"
    failed = "failed"


@dataclass
class Job:
    id: str
    user_id: str
    job_type: str
    status: JobStatus = JobStatus.pending
    progress: int = 0  # 0-100
    message: str = ""
    result: Optional[Dict[str, Any]] = None
    error: Optional[str] = None
    created_at: datetime = field(default_factory=datetime.utcnow)
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None


class JobManager:
    """
    Simple in-memory job manager.
    
    Tracks background job status so the frontend can poll for progress.
    """
    
    _instance = None
    _jobs: Dict[str, Job] = {}
    
    def __new__(cls):
        # Singleton pattern
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._jobs = {}
        return cls._instance
    
    def create_job(self, user_id: str, job_type: str) -> Job:
        """Create a new job and return it."""
        job_id = str(uuid.uuid4())
        job = Job(
            id=job_id,
            user_id=user_id,
            job_type=job_type,
            status=JobStatus.pending,
            message="Job created, waiting to start..."
        )
        self._jobs[job_id] = job
        return job
    
    def get_job(self, job_id: str, user_id: Optional[str] = None) -> Optional[Job]:
        """Get a job by ID, optionally verifying user ownership."""
        job = self._jobs.get(job_id)
        if job and user_id and job.user_id != user_id:
            return None  # User doesn't own this job
        return job
    
    def update_job(
        self,
        job_id: str,
        status: Optional[JobStatus] = None,
        progress: Optional[int] = None,
        message: Optional[str] = None,
        result: Optional[Dict[str, Any]] = None,
        error: Optional[str] = None
    ) -> Optional[Job]:
        """Update job status and progress."""
        job = self._jobs.get(job_id)
        if not job:
            return None
        
        if status:
            job.status = status
            if status == JobStatus.running and not job.started_at:
                job.started_at = datetime.utcnow()
            elif status in (JobStatus.completed, JobStatus.failed):
                job.completed_at = datetime.utcnow()
        
        if progress is not None:
            job.progress = min(100, max(0, progress))
        
        if message:
            job.message = message
        
        if result is not None:
            job.result = result
        
        if error:
            job.error = error
            job.status = JobStatus.failed
        
        return job
    
    def get_user_jobs(self, user_id: str, job_type: Optional[str] = None) -> list[Job]:
        """Get all jobs for a user, optionally filtered by type."""
        jobs = [j for j in self._jobs.values() if j.user_id == user_id]
        if job_type:
            jobs = [j for j in jobs if j.job_type == job_type]
        return sorted(jobs, key=lambda j: j.created_at, reverse=True)
    
    def cleanup_old_jobs(self, max_age_hours: int = 24):
        """Remove jobs older than max_age_hours."""
        cutoff = datetime.utcnow()
        to_remove = []
        for job_id, job in self._jobs.items():
            if job.completed_at:
                age = (cutoff - job.completed_at).total_seconds() / 3600
                if age > max_age_hours:
                    to_remove.append(job_id)
        
        for job_id in to_remove:
            del self._jobs[job_id]


# Global instance
job_manager = JobManager()
