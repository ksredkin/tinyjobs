import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.tinyjobs.database.models import Job, Step
from src.tinyjobs.enums import JobStatus, StepStatus
from src.tinyjobs.repositories.step_repository import StepRepository


@pytest.fixture
async def job(session_factory) -> Job:
    def test_func(name: str) -> None:
        print(name)

    func = f"{test_func.__module__}:{test_func.__name__}"
    func_kwargs = {"name": "ksredkin"}
    status = JobStatus.PENDING
    retries = 1
    retries_left = 0
    ctx_mode = False

    async with session_factory() as session:
        session: AsyncSession  # type: ignore

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

    return job


@pytest.mark.asyncio
async def test_create(session_factory, job) -> None:
    async with session_factory() as session:
        session: AsyncSession  # type: ignore

        step_repo = StepRepository(session)
        step = await step_repo.create(job.id, "get_users")
        await session.commit()

    assert step.job_id == job.id
    assert step.status == StepStatus.PENDING
    assert step.name == "get_users"
    assert step.result is None

    async with session_factory() as session:
        result = await session.execute(select(Step).where(Step.id == step.id))
        database_step = result.scalar_one()

    assert database_step.job_id == step.job_id
    assert database_step.status == step.status
    assert database_step.name == step.name
    assert database_step.result == step.result


@pytest.mark.asyncio
async def test_update_step_status(session_factory, job) -> None:
    async with session_factory() as session:
        session: AsyncSession  # type: ignore

        step = Step(job_id=job.id, name="get_users", status=StepStatus.PENDING)
        session.add(step)
        await session.commit()

    new_status = StepStatus.RUNNING

    async with session_factory() as session:
        step_repo = StepRepository(session)
        updated_step = await step_repo.update_step(step.id, new_status=new_status)
        await session.commit()

    assert updated_step
    assert updated_step.status == new_status

    async with session_factory() as session:
        result = await session.execute(select(Step).where(Step.id == step.id))
        database_step = result.scalar_one()

    assert database_step.status == new_status


@pytest.mark.asyncio
async def test_update_step_without_status(session_factory, job) -> None:
    async with session_factory() as session:
        session: AsyncSession  # type: ignore

        step = Step(job_id=job.id, name="get_users", status=StepStatus.PENDING)
        session.add(step)
        await session.commit()

    async with session_factory() as session:
        step_repo = StepRepository(session)
        updated_step = await step_repo.update_step(step.id)
        await session.commit()

    assert updated_step
    assert step.status == updated_step.status

    async with session_factory() as session:
        result = await session.execute(select(Step).where(Step.id == step.id))
        database_step = result.scalar_one()

    assert database_step.status == step.status


@pytest.mark.asyncio
async def test_update_step_result(session_factory, job) -> None:
    async with session_factory() as session:
        session: AsyncSession  # type: ignore

        step = Step(job_id=job.id, name="get_users", status=StepStatus.PENDING)
        session.add(step)
        await session.commit()

    new_result = "help me"

    async with session_factory() as session:
        step_repo = StepRepository(session)
        updated_step = await step_repo.update_step(step.id, new_result=new_result)
        await session.commit()

    assert updated_step
    assert updated_step.result == new_result

    async with session_factory() as session:
        result = await session.execute(select(Step).where(Step.id == step.id))
        database_step = result.scalar_one()

    assert database_step.result == new_result


@pytest.mark.asyncio
async def test_update_step_without_result(session_factory, job) -> None:
    result = "123"
    async with session_factory() as session:
        session: AsyncSession  # type: ignore

        step = Step(
            job_id=job.id, name="get_users", status=StepStatus.PENDING, result=result
        )
        session.add(step)
        await session.commit()

    async with session_factory() as session:
        step_repo = StepRepository(session)
        updated_step = await step_repo.update_step(step.id)
        await session.commit()

    assert updated_step
    assert updated_step.result == result

    async with session_factory() as session:
        database_result = await session.execute(select(Step).where(Step.id == step.id))
        database_step = database_result.scalar_one()

    assert database_step.result == result


@pytest.mark.asyncio
async def test_update_step_without_step(session_factory, job) -> None:
    async with session_factory() as session:
        step_repo = StepRepository(session)
        updated_step = await step_repo.update_step(107)
        await session.commit()

    assert updated_step is None


@pytest.mark.asyncio
async def test_get_by_job_id(session_factory, job) -> None:
    async with session_factory() as session:
        session: AsyncSession  # type: ignore

        first_step = Step(
            job_id=job.id, name="get_users", status=StepStatus.COMPLETED, result="123"
        )
        second_step = Step(job_id=job.id, name="print_users", status=StepStatus.PENDING)
        session.add(first_step)
        session.add(second_step)
        await session.commit()

    async with session_factory() as session:
        step_repo = StepRepository(session)
        steps = await step_repo.get_by_job_id(job.id)

    assert len(steps) == 2
    assert [
        {"name": s.name, "status": s.status, "result": s.result} for s in steps
    ] == [
        {"name": "get_users", "status": StepStatus.COMPLETED, "result": "123"},
        {"name": "print_users", "status": StepStatus.PENDING, "result": None},
    ]


@pytest.mark.asyncio
async def test_get_by_job_id_without_step(session_factory, job) -> None:
    async with session_factory() as session:
        step_repo = StepRepository(session)
        steps = await step_repo.get_by_job_id(job.id)

    assert len(steps) == 0


@pytest.mark.asyncio
async def test_get_by_job_and_name(session_factory, job) -> None:
    async with session_factory() as session:
        session: AsyncSession  # type: ignore

        step = Step(
            job_id=job.id, name="get_users", status=StepStatus.COMPLETED, result="123"
        )
        session.add(step)
        await session.commit()

    async with session_factory() as session:
        step_repo = StepRepository(session)
        database_step = await step_repo.get_by_job_and_name(job.id, "get_users")
        unreal_step = await step_repo.get_by_job_and_name(job.id, "107")

    assert database_step
    assert database_step.id == step.id
    assert unreal_step is None
