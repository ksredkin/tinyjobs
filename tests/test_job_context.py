from unittest.mock import AsyncMock

import pytest

from src.tinyjobs.enums import JobStatus, StepStatus
from src.tinyjobs.job_context import JobContext
from src.tinyjobs.services.job_service import Job
from src.tinyjobs.services.step_service import Step


@pytest.mark.asyncio
async def test_step_withut_database_data() -> None:
    job = Job(1, lambda: 1, {}, JobStatus.PENDING, ctx_mode=True)

    step_name = "get_name"
    value = "name"

    step_service = AsyncMock()
    step = Step(1, job.id, step_name, StepStatus.PENDING)
    step_service.get_by_job_and_name.return_value = None
    step_service.create.return_value = step

    ctx = JobContext(job.id, step_service)

    @ctx.step(step_name)
    async def get_name() -> str:
        return value

    returned_value = await get_name()

    assert returned_value == value
    step_service.get_by_job_and_name.assert_awaited_with(job.id, step_name)
    step_service.create.assert_awaited_with(job.id, step_name)
    step_service.update_status.assert_awaited_with(step.id, StepStatus.COMPLETED)
    step_service.update_result.assert_awaited_with(step.id, returned_value)


@pytest.mark.asyncio
async def test_step_with_database_data() -> None:
    job = Job(1, lambda: 1, {}, JobStatus.PENDING, ctx_mode=True)

    step_name = "get_name"
    value = "name"

    step_service = AsyncMock()
    step = Step(1, job.id, step_name, StepStatus.COMPLETED, result=value)
    step_service.get_by_job_and_name.return_value = step

    ctx = JobContext(job.id, step_service)

    @ctx.step(step_name)
    async def get_name() -> str:
        raise Exception()

    returned_value = await get_name()

    assert returned_value == value
    step_service.get_by_job_and_name.assert_awaited_with(job.id, step_name)


@pytest.mark.asyncio
async def test_step_with_error() -> None:
    job = Job(1, lambda: 1, {}, JobStatus.PENDING, ctx_mode=True)

    step_name = "get_name"

    step_service = AsyncMock()
    step = Step(1, job.id, step_name, StepStatus.FAILED)
    step_service.get_by_job_and_name.return_value = step

    ctx = JobContext(job.id, step_service)

    class MyException(Exception):
        pass

    @ctx.step(step_name)
    async def get_name() -> str:
        raise MyException()

    with pytest.raises(MyException):
        await get_name()

    step_service.get_by_job_and_name.assert_awaited_with(job.id, step_name)
    step_service.update_status.assert_awaited_with(step.id, StepStatus.FAILED)
