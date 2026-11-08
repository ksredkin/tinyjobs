import json
from dataclasses import dataclass
from typing import Any

from ..database.database import Database
from ..enums import StepStatus
from ..repositories.step_repository import StepRepository


@dataclass
class Step:
    id: int
    job_id: int
    name: str
    status: StepStatus
    result: Any | None = None


class StepService:
    def __init__(self, database: Database) -> None:
        self.database = database

    async def create(self, job_id: int, name: str) -> Step:
        async with self.database.get_async_session() as session:
            step_repo = StepRepository(session)
            step = await step_repo.create(job_id, name)
        return Step(
            step.id,
            step.job_id,
            step.name,
            step.status,
            json.loads(step.result) if step.result else None,
        )

    async def get_by_job_and_name(self, job_id: int, name: str) -> Step | None:
        async with self.database.get_async_session() as session:
            step_repo = StepRepository(session)
            step = await step_repo.get_by_job_and_name(job_id, name)

        if not step:
            return None

        return Step(
            step.id,
            step.job_id,
            step.name,
            step.status,
            json.loads(step.result) if step.result else None,
        )

    async def update_status_and_result(
        self, step_id: int, new_status: StepStatus, new_result: Any
    ) -> None:
        async with self.database.get_async_session() as session:
            step_repo = StepRepository(session)
            await step_repo.update_step(
                step_id=step_id,
                new_status=new_status,
                new_result=json.dumps(new_result),
            )

    async def update_status(self, step_id: int, new_status: StepStatus) -> None:
        async with self.database.get_async_session() as session:
            step_repo = StepRepository(session)
            await step_repo.update_step(step_id=step_id, new_status=new_status)

    async def update_result(self, step_id: int, new_result: Any) -> None:
        async with self.database.get_async_session() as session:
            step_repo = StepRepository(session)
            await step_repo.update_step(
                step_id=step_id, new_result=json.dumps(new_result)
            )
