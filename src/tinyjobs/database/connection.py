from sqlalchemy.ext.asyncio import AsyncEngine, async_sessionmaker, create_async_engine


def get_engine(namespace: str = "main") -> AsyncEngine:
    DATABASE_URL = f"sqlite+aiosqlite:///./{namespace}.db"
    return create_async_engine(DATABASE_URL)


def get_session(async_engine: AsyncEngine) -> async_sessionmaker:
    return async_sessionmaker(bind=async_engine, expire_on_commit=False)
