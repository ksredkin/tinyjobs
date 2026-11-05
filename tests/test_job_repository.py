from src.tinyjobs.database.models import Base
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
import pytest
from src.tinyjobs.repositories.job_repository import JobRepository, Job
from src.tinyjobs.enums import JobStatus
from sqlalchemy import select


@pytest.fixture
async def session_factory() -> async_sessionmaker:
    async_engine = create_async_engine("sqlite+aiosqlite:///:memory:")

    async with async_engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    return async_sessionmaker(bind=async_engine, expire_on_commit=False)


@pytest.mark.asyncio
async def test_create(session_factory) -> None:
    def test_func(name: str) -> None:
        print(name)

    async with session_factory() as session:
        session: AsyncSession
        job_repo = JobRepository(session)
        job = await job_repo.create(f"{test_func.__module__}:{test_func.__name__}", {"name": "ksredkin"}, retries=10, ctx_mode=False)
        await session.commit()

    assert job.func == f"{test_func.__module__}:{test_func.__name__}"
    assert job.func_kwargs == {"name": "ksredkin"}
    assert job.retries == 10
    assert not job.ctx_mode
    assert job.status == JobStatus.PENDING
    assert job.retries_left == 0

    async with session_factory() as session:
        session: AsyncSession
        result = await session.execute(select(Job).where(Job.id == job.id))
        database_job = result.scalar_one()

    assert database_job.func == job.func
    assert database_job.func_kwargs == job.func_kwargs
    assert database_job.retries == job.retries
    assert database_job.ctx_mode == job.ctx_mode
    assert database_job.status == job.status
    assert database_job.retries_left == job.retries_left



@pytest.mark.asyncio
async def test_update_by_id(session_factory) -> None:
    def test_func(name: str) -> None:
        print(name)

    func = f"{test_func.__module__}:{test_func.__name__}"
    func_kwargs = {"name": "ksredkin"}
    status = JobStatus.PENDING
    retries = 1
    retries_left = 0
    ctx_mode = False

    async with session_factory() as session:
        session: AsyncSession
        job = Job(
            func=func,
            func_kwargs=func_kwargs,
            status=status,
            retries=retries,
            retries_left=retries_left,
            ctx_mode=ctx_mode,
        )
        session.add(job)
        await session.commit()

    async with session_factory() as session:
        session: AsyncSession
        job_repo = JobRepository(session)
        new_job = await job_repo.update_by_id(job.id, new_status=JobStatus.RUNNING)
        await session.commit()

    assert new_job.id == job.id
    assert new_job.func == func
    assert new_job.func_kwargs == func_kwargs
    assert new_job.retries == retries
    assert new_job.retries_left == retries_left
    assert new_job.ctx_mode == ctx_mode
    assert new_job.status == JobStatus.RUNNING

    async with session_factory() as session:
        session: AsyncSession
        database_job = await session.get(Job, job.id)

    assert database_job.status == new_job.status 


@pytest.mark.asyncio
async def test_update_by_id_not_found(session_factory) -> None:
    async with session_factory() as session:
        session: AsyncSession
        job_repo = JobRepository(session)
        new_job = await job_repo.update_by_id(1, new_status=JobStatus.RUNNING)
        await session.commit()

    assert new_job is None

    async with session_factory() as session:
        session: AsyncSession
        database_job = await session.get(Job, 1)

    assert database_job is None


@pytest.mark.asyncio
async def test_update_by_id_without_status(session_factory) -> None:
    def test_func(name: str) -> None:
        print(name)

    func = f"{test_func.__module__}:{test_func.__name__}"
    func_kwargs = {"name": "ksredkin"}
    status = JobStatus.PENDING
    retries = 1
    retries_left = 0
    ctx_mode = False

    async with session_factory() as session:
        session: AsyncSession
        job = Job(
            func=func,
            func_kwargs=func_kwargs,
            status=status,
            retries=retries,
            retries_left=retries_left,
            ctx_mode=ctx_mode,
        )
        session.add(job)
        await session.commit()

    async with session_factory() as session:
        session: AsyncSession
        job_repo = JobRepository(session)
        new_job = await job_repo.update_by_id(job.id)
        await session.commit()

    assert new_job.id == job.id
    assert new_job.func == func
    assert new_job.func_kwargs == func_kwargs
    assert new_job.retries == retries
    assert new_job.retries_left == retries_left
    assert new_job.ctx_mode == ctx_mode
    assert new_job.status == job.status

    async with session_factory() as session:
        session: AsyncSession
        database_job = await session.get(Job, job.id)

    assert database_job.status == job.status 


@pytest.mark.asyncio
async def test_add_retry_left_by_id(session_factory) -> None:
    def test_func(name: str) -> None:
        print(name)

    func = f"{test_func.__module__}:{test_func.__name__}"
    func_kwargs = {"name": "ksredkin"}
    status = JobStatus.PENDING
    retries = 1
    retries_left = 0
    ctx_mode = False

    async with session_factory() as session:
        session: AsyncSession
        job = Job(
            func=func,
            func_kwargs=func_kwargs,
            status=status,
            retries=retries,
            retries_left=retries_left,
            ctx_mode=ctx_mode,
        )
        session.add(job)
        await session.commit()

    async with session_factory() as session:
        session: AsyncSession
        job_repo = JobRepository(session)
        new_job = await job_repo.add_retry_left_by_id(job.id)
        await session.commit()

    assert new_job.id == job.id
    assert new_job.func == func
    assert new_job.func_kwargs == func_kwargs
    assert new_job.retries == retries
    assert new_job.retries_left == job.retries_left + 1
    assert new_job.ctx_mode == ctx_mode
    assert new_job.status == job.status

    async with session_factory() as session:
        session: AsyncSession
        database_job = await session.get(Job, job.id)

    assert database_job.retries_left == job.retries_left + 1 


@pytest.mark.asyncio
async def test_add_retry_left_by_id_not_found(session_factory) -> None:
    async with session_factory() as session:
        session: AsyncSession
        job_repo = JobRepository(session)
        new_job = await job_repo.add_retry_left_by_id(1)
        await session.commit()

    assert new_job is None

    async with session_factory() as session:
        session: AsyncSession
        database_job = await session.get(Job, 1)

    assert database_job is None


@pytest.mark.asyncio
async def test_get_active(session_factory) -> None:
    def test_func(name: str) -> None:
        print(name)

    func = f"{test_func.__module__}:{test_func.__name__}"
    func_kwargs = {"name": "ksredkin"}
    status = JobStatus.PENDING
    retries = 1
    retries_left = 0
    ctx_mode = False

    async with session_factory() as session:
        session: AsyncSession
        job = Job(
            func=func,
            func_kwargs=func_kwargs,
            status=status,
            retries=retries,
            retries_left=retries_left,
            ctx_mode=ctx_mode,
        )
        session.add(job)
        await session.commit()

    async with session_factory() as session:
        session: AsyncSession
        job_repo = JobRepository(session)
        active = await job_repo.get_active()

    assert len(active) == 1
    assert active[0].id == job.id
    assert active[0].func == func
    assert active[0].func_kwargs == func_kwargs
    assert active[0].retries == retries
    assert active[0].retries_left == job.retries_left
    assert active[0].ctx_mode == ctx_mode
    assert active[0].status == job.status
