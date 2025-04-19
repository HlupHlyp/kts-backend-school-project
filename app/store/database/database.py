from typing import TYPE_CHECKING, Any

from sqlalchemy import URL
from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.orm import DeclarativeBase

from app.store.database.sqlalchemy_base import BaseModel

if TYPE_CHECKING:
    from app.web.app import Application


class Database:
    def __init__(self, app: "Application") -> None:
        self.app = app

        self.engine: AsyncEngine | None = None
        self._db: type[DeclarativeBase] = BaseModel
        self.session: async_sessionmaker[AsyncSession] | None = None

    def make_db_url(self) -> URL:
        return URL.create(
            database=self.app.config.database.database,
            username=self.app.config.database.user,
            password=self.app.config.database.password,
            host=self.app.config.database.host,
            drivername=self.app.config.database.driver,
        )

    async def connect(self, *args: Any, **kwargs: Any) -> None:
        self.engine = create_async_engine(self.make_db_url())
        self.session = async_sessionmaker(
            self.engine, class_=AsyncSession, expire_on_commit=False
        )

    async def disconnect(self, *args: Any, **kwargs: Any) -> None:
        await self.engine.dispose()
