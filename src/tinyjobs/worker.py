import asyncio
from dataclasses import dataclass
from .enums import JobStatus, StepStatus
from typing import Any
from .logger import get_logger
from .database.database import Database
from .repositories.job_repository import JobRepository
from .repositories.step_repository import StepRepository
import json

logger = get_logger("Worker")

@dataclass
class Step:
    id: int
    job_id: int
    name: str
    status: StepStatus
    result: Any|None

class JobContext:
    def __init__(self, job_id: int) -> None:
        self.job_id = job_id
        self.database = None

    async def get_step_by_name_and_job(self, job_id: int, name: str) -> Step|None:
        async with self.database.get_async_session() as session:
            step_repo = StepRepository(session)
            step = await step_repo.get_by_name_and_job(job_id, name)

        if not step:
            return None

        return Step(step.id, step.job_id, step.name, step.status, json.loads(step.result) if step.result else None)

    async def update_step_status_by_id(self, step_id: int, new_status: StepStatus) -> None:
        async with self.database.get_async_session() as session:
            step_repo = StepRepository(session)
            await step_repo.update_step(step_id=step_id, new_status=new_status)

    async def update_step_result_by_id(self, step_id: int, new_result: Any) -> None:
        async with self.database.get_async_session() as session:
            step_repo = StepRepository(session)
            await step_repo.update_step(step_id=step_id, new_result=json.dumps(new_result))

    async def create(self, job_id: int, name: str) -> Step:
        async with self.database.get_async_session() as session:
            step_repo = StepRepository(session)
            step = await step_repo.create(job_id=job_id, name=name)
        return Step(step.id, step.job_id, step.name, step.status, json.loads(step.result) if step.result else None)

    def step(self, step_name: str):
        if not Database._instance:
            return
        self.database = Database()
        def decorator_step(func):
            async def wrapper(*args, **kwargs):
                logger.debug(f"Выполнение шага {step_name}.")
                step = await self.get_step_by_name_and_job(self.job_id, step_name)

                if not step:
                    step = await self.create(self.job_id, step_name)

                if step.status not in [StepStatus.COMPLETED, StepStatus.FAILED]:
                    await self.update_step_status_by_id(step.id, StepStatus.RUNNING)
                    
                    result = await func(*args, **kwargs)
                    
                    logger.debug(f"Данные получены путем выполнения шага {step_name}.")
                    await self.update_step_status_by_id(step.id, StepStatus.COMPLETED)
                    await self.update_step_result_by_id(step.id, result)
                    
                    return result
                else:
                    logger.debug(f"Данные шага {step_name} получены из базы.")
                    return step.result
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
                        async_function_kwargs["ctx"] = JobContext(job.id)
                    await job.async_function(**async_function_kwargs)
                    job.status = JobStatus.COMPLETED
                    await self.update_database_job(job.id, JobStatus.COMPLETED)
                    break
                except Exception:
                    if (retrying + 1) == job.retries:
                        await self.update_database_job(job.id, JobStatus.FAILED)
                        job.status = JobStatus.FAILED
                        break
