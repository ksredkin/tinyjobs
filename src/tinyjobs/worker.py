import asyncio
from collections.abc import Callable
from dataclasses import dataclass
from typing import Any

from .database.database import Database
from .enums import JobStatus
from .job_context import JobContext
from .logger import get_logger
from .repositories.job_repository import JobRepository

logger = get_logger("Worker")


@dataclass
class Job:
    id: int
    async_function: Callable[..., Any]
    async_function_kwargs: dict[str, Any]
    status: JobStatus
    retries: int = 1
    retries_left: int = 0
    ctx_mode: bool = False


class Worker:
    def __init__(self) -> None:
        self.database = Database()

    async def update_database_job(self, job_id: int, new_status: JobStatus) -> None:
        async with self.database.get_async_session() as session:
            job_repo = JobRepository(session)
            await job_repo.update_by_id(job_id, new_status)

    async def process_jobs(self, jobs: asyncio.Queue[Job]) -> None:
        while True:
            job = await jobs.get()

            job.status = JobStatus.RUNNING
            await self.update_database_job(job.id, JobStatus.RUNNING)

            for retrying in range(job.retries):
                try:
                    async_function_kwargs = {**job.async_function_kwargs}
                    if job.ctx_mode:
                        async_function_kwargs["ctx"] = JobContext(job.id)
                    await job.async_function(**async_function_kwargs)
                    job.status = JobStatus.COMPLETED
                    await self.update_database_job(job.id, JobStatus.COMPLETED)
                    break
                except Exception:  # noqa
                    if (retrying + 1) == job.retries:
                        await self.update_database_job(job.id, JobStatus.FAILED)
                        job.status = JobStatus.FAILED
                        break
