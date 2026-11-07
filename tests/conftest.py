import pytest
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from src.tinyjobs.database.models import Base


@pytest.fixture
async def session_factory() -> async_sessionmaker:
    async_engine = create_async_engine("sqlite+aiosqlite:///:memory:")

    async with async_engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    return async_sessionmaker(bind=async_engine, expire_on_commit=False)
