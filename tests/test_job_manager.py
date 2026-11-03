from src.tinyjobs.job_manager import JobManager
import src.tinyjobs.job_manager as job_manager_module
from unittest.mock import Mock, AsyncMock
import pytest

@pytest.fixture
def job_manager_dependencies(monkeypatch: pytest.MonkeyPatch) -> tuple[AsyncMock, AsyncMock, AsyncMock]:
    database = Mock()
    database.init_db = AsyncMock(return_value=None)

    job_service = Mock()
    job_service.get_active = AsyncMock(return_value=[])
    job_service.create = AsyncMock()

    step_service = Mock()

    monkeypatch.setattr(job_manager_module, "Database", Mock(return_value=database))
    monkeypatch.setattr(job_manager_module, "JobService", Mock(return_value=job_service))
    monkeypatch.setattr(job_manager_module, "StepService", Mock(return_value=step_service))
    
    return database, job_service, step_service

@pytest.mark.asyncio
async def test_create_job_service(job_manager_dependencies) -> None:
    database, job_service, _ = job_manager_dependencies
    
    manager = JobManager(workers=0)
    await manager._startup_task

    assert manager.jobs.qsize() == 0
    assert manager.jobs_by_id == {}

    database.init_db.assert_awaited()
    job_service.get_active.assert_awaited()


@pytest.mark.asyncio
async def test_enqueue_job(job_manager_dependencies) -> None:
    manager = JobManager(workers=0)
    await manager._startup_task

    assert manager.jobs.qsize() == 0
    assert manager.jobs_by_id == {}

    job = Mock()
    job.id = 123

    await manager._enqueue_job(job)

    assert await manager.jobs.get() is job
    assert manager.jobs_by_id[job.id] is job


@pytest.mark.asyncio
async def test_add(job_manager_dependencies) -> None:
    _, job_service, _ = job_manager_dependencies

    job = Mock()
    job.id = 1
    job_service.create.return_value = job
    
    manager = JobManager(workers=0)
    await manager._startup_task

    assert manager.jobs.qsize() == 0
    assert manager.jobs_by_id == {}

    async_function = Mock()
    async_function_kwargs = {"Hello": "World"}
    retries = 100
    ctx_mode = True
    
    added_job_id = await manager.add(async_function, async_function_kwargs, retries, ctx_mode)
    job_service.create.assert_awaited_once_with(async_function, async_function_kwargs, retries, ctx_mode)
    assert added_job_id == job.id

    assert manager.jobs_by_id[job.id] is job
    assert manager.jobs.get_nowait() is job


@pytest.mark.asyncio
async def test_get(job_manager_dependencies) -> None:
    _, job_service, _ = job_manager_dependencies

    job = Mock()
    job.id = 1
    job_service.create.return_value = job
    
    manager = JobManager(workers=0)
    await manager._startup_task

    async def example():
        pass
    
    added_job_id = await manager.add(
        async_function=example,
        async_function_kwargs={},
        retries=1,
        ctx_mode=False,
    )

    assert await manager.get(0) is None 
    assert await manager.get(added_job_id) is job


@pytest.mark.asyncio
async def test_restoring_tasks(job_manager_dependencies) -> None:
    _, job_service, _ = job_manager_dependencies

    job = Mock()
    job.id = 1
    job_service.get_active = AsyncMock(return_value=[job])

    _enqueue_job = AsyncMock()
    setattr(JobManager, "_enqueue_job", _enqueue_job)
    
    manager = JobManager(workers=0)
    await manager._startup_task

    _enqueue_job.assert_awaited_with(job)
