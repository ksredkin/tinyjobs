from .worker import Worker, Job, JobStatus
import asyncio
from typing import Any
from .database.database import Database
from .repositories.job_repository import JobRepository
import importlib

class JobManager:
    def __init__(self, namespace: str = "main", workers: int = 10) -> None:
        self.jobs: asyncio.Queue[Job] = asyncio.Queue()
        self.jobs_by_id: dict[int, Job] = {}

        self.workers: list[Worker] = [Worker() for _ in range(workers)]

        self.database = Database(namespace)
        self._worker_tasks: list[asyncio.Task[None]] = []

        loop = asyncio.get_running_loop()
        self._initialization_task = loop.create_task(self.database.init_db())
        loop.create_task(self._start_workers())

    def find_function(self, function: str) -> function:
        module_name, func_name = function.split(':')

        module = importlib.import_module(module_name)

        func_obj = getattr(module, func_name)
        return func_obj

    async def get_active_jobs(self) -> list[Job]:
        async with self.database.get_async_session() as session:
            job_repo = JobRepository(session)
            db_jobs = await job_repo.get_active()
        return [Job(id=db_job.id, async_function=self.find_function(db_job.func), async_function_kwargs=db_job.func_kwargs, status=db_job.status, retries=db_job.retries, retries_left=db_job.retries_left, ctx_mode=db_job.ctx_mode) for db_job in db_jobs]

    async def _start_workers(self) -> None:
        await self._initialization_task

        active_jobs = await self.get_active_jobs()
        for job in active_jobs:
            await self.jobs.put(job)
            self.jobs_by_id[job.id] = job

        self._worker_tasks = [
            asyncio.create_task(worker.process_jobs(self.jobs))
            for worker in self.workers
        ]

    async def add(self, async_function: function, async_function_kwargs: dict[str, Any] = {}, retries: int = 1, ctx_mode: bool = False) -> int:
        await self._initialization_task

        async with self.database.get_async_session() as session:
            job_rep = JobRepository(session)
            job_model = await job_rep.create(func=f"{async_function.__module__}:{async_function.__name__}", func_kwargs=async_function_kwargs, retries=retries, ctx_mode=ctx_mode)

        job = Job(id=job_model.id, async_function=async_function, async_function_kwargs=async_function_kwargs, status=job_model.status, retries=retries, retries_left=0, ctx_mode=ctx_mode)
    
        self.jobs_by_id[job.id] = job
        await self.jobs.put(job)
        
        return job.id

    async def get(self, job_id: int) -> Job|None:
        return self.jobs_by_id.get(job_id)
