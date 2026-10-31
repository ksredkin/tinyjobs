import asyncio
from dataclasses import dataclass
from .enums import JobStatus
from typing import Any
from .logger import get_logger
from .database.database import Database
from .repositories.job_repository import JobRepository

logger = get_logger("Worker")

class JobContext:
    def __init__(self, job_id: int) -> None:
        self.job_id = job_id
        self.done_steps: dict[str, Any] = {}

    def step(self, step: str):
        def decorator_step(func):
            async def wrapper(*args, **kwargs):
                logger.debug(f"Выполнение шага {step}.")
                if step not in self.done_steps.keys():
                    result = await func(*args, **kwargs)
                    logger.debug(f"Данные получены путем выполнения шага {step}.")
                    self.done_steps[step] = result
                    return result
                else:
                    logger.debug(f"Данные шага {step} получены из базы.")
                    return self.done_steps.get(step)
            return wrapper
        return decorator_step

@dataclass
class Job:
    id: int
    async_function: function
    async_function_kwargs: dict[str, Any]
    status: JobStatus
    retries: int = 1
    retries_left: int = 0
    ctx_mode: bool = False
    ctx: JobContext = JobContext(id)

class Worker:
    def __init__(self) -> None:
        self.database = None

    async def update_database_job(self, job_id: int, new_status: JobStatus) -> None:
        async with self.database.get_async_session() as session:
            job_repo = JobRepository(session)
            await job_repo.update_by_id(job_id, new_status)

    async def process_jobs(self, jobs: asyncio.Queue[Job]) -> None:
        self.database = Database()
        while True:
            job = await jobs.get()
            
            job.status = JobStatus.RUNNING
            await self.update_database_job(job.id, JobStatus.RUNNING)

            for retrying in range(job.retries):
                try:
                    async_function_kwargs = {**job.async_function_kwargs}
                    if job.ctx_mode:
                        async_function_kwargs["ctx"] = job.ctx
                    await job.async_function(**async_function_kwargs)
                    job.status = JobStatus.COMPLETED
                    await self.update_database_job(job.id, JobStatus.COMPLETED)
                    break
                except Exception as e:
                    raise e
                    if (retrying + 1) == job.retries:
                        await self.update_database_job(job.id, JobStatus.FAILED)
                        job.status = JobStatus.FAILED
                        break
