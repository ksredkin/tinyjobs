import importlib
from dataclasses import dataclass
from typing import Any, Callable

from ..database.database import Database
from ..enums import JobStatus
from ..repositories.job_repository import JobRepository


@dataclass
class Job:
    id: int
    async_function: Callable[..., Any]
    async_function_kwargs: dict[str, Any]
    status: JobStatus
    retries: int = 1
    retries_left: int = 0
    ctx_mode: bool = False


class JobService:
    def __init__(self, database: Database) -> None:
        self.database = database

    def find_function(self, function: str) -> Callable[..., Any]:
        module_name, func_name = function.split(":")
        module = importlib.import_module(module_name)
        return getattr(module, func_name)

    async def get_active(self) -> list[Job]:
        async with self.database.get_async_session() as session:
            job_repo = JobRepository(session)
            db_jobs = await job_repo.get_active()
        return [
            Job(
                db_job.id,
                self.find_function(db_job.func),
                db_job.func_kwargs,
                db_job.status,
                db_job.retries,
                db_job.retries_left,
                db_job.ctx_mode,
            )
            for db_job in db_jobs
        ]

    async def get_by_id(self, job_id: int) -> Job | None:
        async with self.database.get_async_session() as session:
            job_repo = JobRepository(session)
            job_model = await job_repo.get_by_id(job_id)
            return (
                Job(
                    job_model.id,
                    self.find_function(job_model.func),
                    job_model.func_kwargs,
                    job_model.status,
                    job_model.retries,
                    job_model.retries_left,
                    job_model.ctx_mode,
                )
                if job_model
                else None
            )

    async def create(
        self,
        func: Callable[..., Any],
        func_kwargs: dict[str, Any] = {},
        retries: int = 1,
        ctx_mode: bool = False,
    ) -> Job:
        async with self.database.get_async_session() as session:
            job_repo = JobRepository(session)
            job_model = await job_repo.create(
                f"{func.__module__}:{func.__name__}",
                func_kwargs,
                retries,
                ctx_mode,
            )

        return Job(
            job_model.id,
            func,
            func_kwargs,
            job_model.status,
            retries,
            0,
            ctx_mode,
        )

    async def update_status(self, job_id: int, new_status: JobStatus) -> None:
        async with self.database.get_async_session() as session:
            job_repo = JobRepository(session)
            await job_repo.update_by_id(job_id, new_status)

    async def add_retry_left(self, job_id: int) -> None:
        async with self.database.get_async_session() as session:
            job_repo = JobRepository(session)
            await job_repo.add_retry_left_by_id(job_id)
