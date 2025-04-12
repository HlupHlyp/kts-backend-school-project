from sqlalchemy import select, update
from sqlalchemy.engine.result import ChunkedIteratorResult

from app.base.base_accessor import BaseAccessor
from app.blackjack.models import GameSessionModel


class BlackjackAccessor(BaseAccessor):
    async def create_g_session(
        self,
        chat_id: int,
    ) -> GameSessionModel:
        g_session = await self.get_g_session_by_chat(chat_id)
        if g_session is None:
            g_session = GameSessionModel(chat_id=chat_id, status="sleeping")
            async with self.app.database.session() as session:
                session.add(g_session)
                await session.commit()
        return g_session

    async def get_g_session_by_chat(
        self,
        chat_id: int,
    ) -> GameSessionModel | None:
        async with self.app.database.session() as session:
            g_sessions: ChunkedIteratorResult = await session.execute(
                select(GameSessionModel).where(
                    GameSessionModel.chat_id == chat_id
                )
            )
            return g_sessions.scalar()

    async def set_g_session_status(
        self, chat_id: int, status: str
    ) -> GameSessionModel | None:
        g_session = await self.get_g_session_by_chat(chat_id)
        if g_session is not None:
            async with self.app.database.session() as session:
                g_sessions: ChunkedIteratorResult = await session.execute(
                    update(GameSessionModel)
                    .where(GameSessionModel.chat_id == chat_id)
                    .values(status=status)
                )
        return g_sessions.scalar()
