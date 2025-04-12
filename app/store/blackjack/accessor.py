# from collections.abc import Iterable, Sequence
# from sqlalchemy import select, insert
# from sqlalchemy.exc import IntegrityError
# from sqlalchemy.orm import selectinload

from app.base.base_accessor import BaseAccessor
from app.blackjack.models import (
    # HandModel,
    # PlayerModel,
    GameSessionModel,
)


class BlackjackAccessor(BaseAccessor):
    async def create_hand(
        self,
        chat_id: int,
    ) -> GameSessionModel:
        game_session = GameSessionModel(chat_id=chat_id, status="sleeping")
        async with self.app.database.session() as session:
            session.add(game_session)
            await session.commit()
        return game_session
        # raise NotImplementedError
