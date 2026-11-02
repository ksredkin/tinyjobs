import asyncio

from .enums import JobStatus
from .job_context import JobContext
from .logger import get_logger
from .services.job_service import Job, JobService
from .services.step_service import StepService

logger = get_logger("Worker")


class Worker:
    def __init__(self, job_service: JobService, step_service: StepService) -> None:
        self.job_service = job_service
        self.step_service = step_service

    async def process_jobs(self, jobs: asyncio.Queue[Job]) -> None:
        while True:
            job = await jobs.get()

            job.status = JobStatus.RUNNING
            await self.job_service.update_status(job.id, JobStatus.RUNNING)

            for retrying in range(job.retries):
                try:
                    async_function_kwargs = {**job.async_function_kwargs}
                    if job.ctx_mode:
                        async_function_kwargs["ctx"] = JobContext(
                            job.id, self.step_service
                        )
                    await job.async_function(**async_function_kwargs)
                    job.status = JobStatus.COMPLETED
                    await self.job_service.update_status(job.id, JobStatus.COMPLETED)
                    break
                except Exception:  # noqa
                    if (retrying + 1) == job.retries:
                        await self.job_service.update_status(job.id, JobStatus.FAILED)
                        job.status = JobStatus.FAILED
                        break
                finally:
                    await self.job_service.add_retry_left(job.id)
