from sqlalchemy import select, update

from app.base.base_accessor import BaseAccessor
from app.blackjack.models import GameSessionModel
from app.blackjack.models import GameSessionStatus


class BlackjackAccessor(BaseAccessor):
    async def create_game_session(
        self,
        chat_id: int,
    ) -> GameSessionModel:
        game_session = await self.get_game_session_by_chat(chat_id)
        if game_session is None:
            game_session = GameSessionModel(chat_id=chat_id, status="sleeping")
            async with self.app.database.session() as session:
                session.add(game_session)
                await session.commit()
        return game_session

    async def get_game_session_by_chat(
        self,
        chat_id: int,
    ) -> GameSessionModel | None:
        async with self.app.database.session() as session:
            return await session.scalar(
                select(GameSessionModel).where(
                    GameSessionModel.chat_id == chat_id
                )
            )

    async def set_game_session_status(
        self, chat_id: int, status: GameSessionStatus
    ) -> None:
        game_session = await self.get_game_session_by_chat(chat_id)
        if game_session is not None:
            async with self.app.database.session() as session:
                await session.execute(
                    update(GameSessionModel)
                    .where(GameSessionModel.chat_id == chat_id)
                    .values(status=status)
                )
                await session.commit()

    async def set_game_session_users_num(
        self, chat_id: int, users_num: int
    ) -> None:
        game_session = await self.get_game_session_by_chat(chat_id)
        if game_session is not None:
            async with self.app.database.session() as session:
                await session.execute(
                    update(GameSessionModel)
                    .where(GameSessionModel.chat_id == chat_id)
                    .values(num_users=users_num)
                )
                await session.commit()
