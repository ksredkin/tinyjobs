import asyncio
from unittest.mock import AsyncMock, Mock

import pytest

from src.tinyjobs.enums import JobStatus
from src.tinyjobs.job_context import JobContext
from src.tinyjobs.worker import Worker


@pytest.mark.asyncio
async def test_process_jobs(monkeypatch: pytest.MonkeyPatch) -> None:
    job_service = AsyncMock()
    step_service = AsyncMock()

    worker = Worker(job_service, step_service)

    class BreakException(Exception):
        pass

    _process_job = AsyncMock()
    _process_job.side_effect = BreakException()

    monkeypatch.setattr(worker, "_process_job", _process_job)

    job = Mock()

    jobs_queue: asyncio.Queue = asyncio.Queue()
    await jobs_queue.put(job)

    with pytest.raises(BreakException):
        await worker.process_jobs(jobs_queue)
    _process_job.assert_awaited_with(job)


@pytest.mark.asyncio
async def test_process_job_successful() -> None:
    job_service = AsyncMock()
    step_service = AsyncMock()

    worker = Worker(job_service, step_service)

    job = Mock()
    job.id = 1
    job.retries = 1
    job.status = JobStatus.PENDING
    job.async_function = AsyncMock()
    job.async_function_kwargs = {"Hello": "World"}
    job.ctx_mode = False

    await worker._process_job(job)

    job.async_function.assert_awaited_with(**job.async_function_kwargs)
    assert job.status == JobStatus.COMPLETED
    job_service.update_status.assert_awaited_with(job.id, JobStatus.COMPLETED)
    job_service.add_retry_left.assert_awaited_with(job.id)


@pytest.mark.asyncio
async def test_process_job_with_ctx_mode() -> None:
    job_service = AsyncMock()
    step_service = AsyncMock()

    worker = Worker(job_service, step_service)

    job = Mock()
    job.id = 1
    job.retries = 1
    job.status = JobStatus.PENDING
    job.async_function = AsyncMock()
    job.async_function_kwargs = {"Hello": "World"}
    job.ctx_mode = True

    await worker._process_job(job)

    job.async_function.assert_awaited_once()
    call_kwargs = job.async_function.await_args.kwargs
    ctx = call_kwargs.pop("ctx")

    assert isinstance(ctx, JobContext)
    assert ctx.job_id == job.id
    assert ctx.step_service is step_service
    assert call_kwargs == job.async_function_kwargs
    assert job.status == JobStatus.COMPLETED
    job_service.update_status.assert_awaited_with(job.id, JobStatus.COMPLETED)


@pytest.mark.asyncio
async def test_process_job_with_exception() -> None:
    job_service = AsyncMock()
    step_service = AsyncMock()

    worker = Worker(job_service, step_service)

    class MyException(Exception):
        pass

    job = Mock()
    job.id = 1
    job.retries = 1
    job.status = JobStatus.PENDING
    async_function = AsyncMock()
    async_function.side_effect = MyException()
    job.async_function = async_function
    job.async_function_kwargs = {"Hello": "World"}
    job.ctx_mode = False

    await worker._process_job(job)

    job.async_function.assert_awaited_with(**job.async_function_kwargs)
    job_service.add_retry_left.assert_awaited_with(job.id)
    assert job.status == JobStatus.FAILED
    job_service.update_status.assert_awaited_with(job.id, JobStatus.FAILED)
