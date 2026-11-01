import json
from dataclasses import dataclass
from typing import Any

from .database.database import Database
from .enums import StepStatus
from .logger import get_logger
from .repositories.step_repository import StepRepository

logger = get_logger("JobContext")


@dataclass
class Step:
    id: int
    job_id: int
    name: str
    status: StepStatus
    result: Any | None


class JobContext:
    def __init__(self, job_id: int) -> None:
        self.job_id = job_id
        self.database = Database()

    async def get_step_by_name_and_job(self, job_id: int, name: str) -> Step | None:
        async with self.database.get_async_session() as session:
            step_repo = StepRepository(session)
            step = await step_repo.get_by_name_and_job(job_id, name)

        if not step:
            return None

        return Step(
            step.id,
            step.job_id,
            step.name,
            step.status,
            json.loads(step.result) if step.result else None,
        )

    async def update_step_status_by_id(
        self, step_id: int, new_status: StepStatus
    ) -> None:
        async with self.database.get_async_session() as session:
            step_repo = StepRepository(session)
            await step_repo.update_step(step_id=step_id, new_status=new_status)

    async def update_step_result_by_id(self, step_id: int, new_result: Any) -> None:
        async with self.database.get_async_session() as session:
            step_repo = StepRepository(session)
            await step_repo.update_step(
                step_id=step_id, new_result=json.dumps(new_result)
            )

    async def create(self, job_id: int, name: str) -> Step:
        async with self.database.get_async_session() as session:
            step_repo = StepRepository(session)
            step = await step_repo.create(job_id=job_id, name=name)
        return Step(
            step.id,
            step.job_id,
            step.name,
            step.status,
            json.loads(step.result) if step.result else None,
        )

    def step(self, step_name: str):
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
