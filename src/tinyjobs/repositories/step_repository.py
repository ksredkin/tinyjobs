from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from sqlalchemy.orm import selectinload
from ..database.models import Step
from ..enums import StepStatus
from typing import Any

NOT_SET = object()

class StepRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def get_by_job_id(self, job_id: int) -> list[Step]:
        result = await self.session.execute(select(Step).where(Step.job_id == job_id))
        return [step for step in result.scalars().all()]

    async def get_by_name_and_job(self, job_id: int, name: str) -> Step|None:
        result = await self.session.execute(select(Step).where(Step.job_id == job_id, Step.name == name))
        return result.scalar_one_or_none()

    async def create(self, job_id: int, name: str) -> Step:
        step = Step(job_id=job_id, name=name, status=StepStatus.PENDING)

        self.session.add(step)
        await self.session.flush()

        return step

    async def update_step(self, step_id: int, new_status: StepStatus|object = NOT_SET, new_result: Any|None = NOT_SET) -> Step|None:
        step = await self.session.get(Step, step_id)

        if not step:
            return None

        if new_status is not NOT_SET:
            step.status = new_status

        if new_result is not NOT_SET:
            step.result = new_result

        await self.session.flush()
        return step
