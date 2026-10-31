from .connection import get_session, get_engine
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, AsyncEngine
from typing import AsyncGenerator
from .models import Base
from ..logger import get_logger
from contextlib import asynccontextmanager

logger = get_logger("Database")

class Database:
    _instance = None

    def __new__(cls, namespace: str|None = None) -> "Database":
        if not cls._instance:
            cls._instance = super().__new__(cls)
            cls._instance.engine = get_engine(namespace)
            cls._instance.sessionmaker = get_session(cls._instance.engine)
        return cls._instance

    @asynccontextmanager
    async def get_async_session(self) -> AsyncGenerator[AsyncSession, None]:
        self.sessionmaker: async_sessionmaker[AsyncSession]
        async with self.sessionmaker() as session:
            try:
                yield session
                await session.commit()
            except Exception as e:
                await session.rollback()
                raise e

    async def init_db(self) -> None:
        self.engine: AsyncEngine
        async with self.engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
            await conn.commit()
            logger.debug("База данных инициализирована")
