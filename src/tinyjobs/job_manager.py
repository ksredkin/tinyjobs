import asyncio
from typing import Any, Callable

from .database.database import Database
from .services.job_service import JobService
from .services.step_service import StepService
from .worker import Job, Worker


class JobManager:
    def __init__(self, namespace: str = "main", workers: int = 10) -> None:
        self.jobs: asyncio.Queue[Job] = asyncio.Queue()
        self.jobs_by_id: dict[int, Job] = {}

        self.database = Database(namespace)
        self.job_service = JobService(self.database)
        self.step_service = StepService(self.database)

        self.workers: list[Worker] = [
            Worker(self.job_service, self.step_service) for _ in range(workers)
        ]

        self._worker_tasks: list[asyncio.Task[None]] = []

        loop = asyncio.get_running_loop()
        self._initialization_task = loop.create_task(self.database.init_db())
        self._startup_task = loop.create_task(self._start_workers())

    async def _enqueue_job(self, job: Job) -> None:
        self.jobs_by_id[job.id] = job
        await self.jobs.put(job)

    async def _start_workers(self) -> None:
        await self._initialization_task

        active_jobs = await self.job_service.get_active()
        for job in active_jobs:
            await self._enqueue_job(job)

        self._worker_tasks = [
            asyncio.create_task(worker.process_jobs(self.jobs))
            for worker in self.workers
        ]

    async def add(
        self,
        async_function: Callable[..., Any],
        async_function_kwargs: dict[str, Any] = {},
        retries: int = 1,
        ctx_mode: bool = False,
    ) -> int:
        await self._startup_task
        job = await self.job_service.create(
            async_function, async_function_kwargs, retries, ctx_mode
        )
        await self._enqueue_job(job)
        return job.id

    async def get(self, job_id: int) -> Job | None:
        job = self.jobs_by_id.get(job_id)

        if not job:
            job = await self.job_service.get_by_id(job_id)

        return job
