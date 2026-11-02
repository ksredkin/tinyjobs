from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from ..database.models import Job
from ..enums import JobStatus

NOT_SET = object()


class JobRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def get_active(self) -> list[Job]:
        result = await self.session.execute(
            select(Job)
            .where(Job.status.in_([JobStatus.PENDING, JobStatus.RUNNING]))
            .options(selectinload(Job.steps))
        )
        return [job for job in result.scalars().all()]

    async def create(
        self, func: str, func_kwargs: dict[str, str | int], retries: int, ctx_mode: bool
    ) -> Job:
        job = Job(
            func=func,
            func_kwargs=func_kwargs,
            status=JobStatus.PENDING,
            retries=retries,
            retries_left=0,
            ctx_mode=ctx_mode,
        )
        self.session.add(job)
        await self.session.flush()
        return job

    async def update_by_id(
        self, job_id: int, new_status: JobStatus | object = NOT_SET
    ) -> Job | None:
        job = await self.session.get(Job, job_id)

        if not job:
            return None

        if isinstance(new_status, JobStatus):
            job.status = new_status

        return job

    async def add_retry_left_by_id(
            self, job_id: int
        ) -> Job | None:
            job = await self.session.get(Job, job_id)
    
            if not job:
                return None
    
            job.retries_left += 1
            return job
