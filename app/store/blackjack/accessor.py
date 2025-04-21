from sqlalchemy import select, update, func
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload, joinedload
from sqlalchemy.sql import text

from app.base.base_accessor import BaseAccessor
from app.blackjack.models import (
    GameSessionModel,
    GameSessionStatus,
    ParticipantModel,
    ParticipantStatus,
    PlayerModel,
)
from app.store.bot.exceptions import (
    GameSessionNotFoundError,
    ParticipantNotFoundError,
    PlayerNotFoundError,
)
from app.store.bot.dataclasses import Cards

DEFAULT_BALANCE = 10000


class BlackjackAccessor(BaseAccessor):
    async def get_or_create_game_session(
        self,
        session: AsyncSession,
        chat_id: int,
    ) -> GameSessionModel:
        game_session = await self.get_game_session_by_chat(
            chat_id=chat_id, session=session
        )
        if game_session is None:
            game_session = GameSessionModel(
                chat_id=chat_id, status=GameSessionStatus.SLEEPING
            )
            session.add(game_session)
        return game_session

    async def get_game_session_by_chat(
        self,
        session: AsyncSession,
        chat_id: int,
    ) -> GameSessionModel | None:
        return await session.scalar(
            select(GameSessionModel)
            .where(GameSessionModel.chat_id == chat_id)
            .options(selectinload(GameSessionModel.participants))
        )

    async def check_game_session(
        self, session: AsyncSession, chat_id: int
    ) -> GameSessionModel:
        game_session = await self.get_game_session_by_chat(
            chat_id=chat_id, session=session
        )
        if game_session is None:
            raise GameSessionNotFoundError(chat_id)
        return game_session

    async def set_game_session_users_num(
        self, session: AsyncSession, chat_id: int, users_num: int
    ) -> None:
        await self.check_game_session(chat_id=chat_id, session=session)
        await session.execute(
            update(GameSessionModel)
            .where(GameSessionModel.chat_id == chat_id)
            .values(num_users=users_num)
        )

    async def set_game_session_status(
        self, session: AsyncSession, chat_id: int, status: GameSessionStatus
    ) -> None:
        await self.check_game_session(chat_id=chat_id, session=session)
        await session.execute(
            update(GameSessionModel)
            .where(GameSessionModel.chat_id == chat_id)
            .values(status=status)
        )

    async def get_player_by_tg_id(
        self, session: AsyncSession, tg_id: int
    ) -> PlayerModel | None:
        return await session.scalar(
            select(PlayerModel).where(PlayerModel.tg_id == tg_id)
        )

    async def get_or_create_player(
        self, tg_id: int, session: AsyncSession, username: str
    ) -> None:
        player = await self.get_player_by_tg_id(tg_id=tg_id, session=session)
        if player is None:
            player = PlayerModel(
                tg_id=tg_id, username=username, balance=DEFAULT_BALANCE
            )
            session.add(player)
        return player

    async def check_player(
        self, session: AsyncSession, tg_id: int
    ) -> PlayerModel:
        player = await self.get_player_by_tg_id(tg_id=tg_id, session=session)
        if player is None:
            raise PlayerNotFoundError(tg_id)
        return player

    async def get_participant_by_tg_and_chat_id(
        self, tg_id: int, chat_id: int, session: AsyncSession
    ) -> ParticipantModel | None:
        player = await self.get_player_by_tg_id(tg_id=tg_id, session=session)
        if player is None:
            return None
        game_session = await self.check_game_session(
            chat_id=chat_id, session=session
        )
        return await session.scalar(
            select(ParticipantModel).where(
                ParticipantModel.player_id == player.id,
                ParticipantModel.game_session_id == game_session.id,
            )
        )

    async def get_or_create_participant(
        self, tg_id: int, username: str, chat_id: int, session: AsyncSession
    ) -> ParticipantModel | None:
        participant = await self.get_participant_by_tg_and_chat_id(
            session=session, tg_id=tg_id, chat_id=chat_id
        )
        if participant is None:
            player = await self.get_or_create_player(
                tg_id=tg_id, session=session, username=username
            )
            game_session = await self.check_game_session(
                chat_id=chat_id, session=session
            )
            participant = ParticipantModel(
                game_session_id=game_session.id,
                player_id=player.id,
                status=ParticipantStatus.SLEEPING,
            )
            session.add(participant)
        return await self.get_participant_by_tg_and_chat_id(
            session=session, tg_id=tg_id, chat_id=chat_id
        )

    async def get_participant_by_id(
        self, participant_id: int, session: AsyncSession
    ) -> ParticipantModel | None:
        return await session.scalar(
            select(ParticipantModel)
            .where(ParticipantModel.id == participant_id)
            .options(joinedload(ParticipantModel.player))
        )

    async def check_participant_by_id(
        self, participant_id: int, session: AsyncSession
    ) -> ParticipantModel:
        participant = await self.get_participant_by_id(
            participant_id=participant_id, session=session
        )
        if participant is None:
            raise ParticipantNotFoundError(participant_id)
        return participant

    async def set_participant_status(
        self,
        participant_id: int,
        status: ParticipantStatus,
        session: AsyncSession,
    ) -> None:
        await self.check_participant_by_id(
            participant_id=participant_id, session=session
        )
        await session.execute(
            update(ParticipantModel)
            .where(ParticipantModel.id == participant_id)
            .values(status=status)
        )

    async def set_participant_bet(
        self, participant_id: int, bet: int, session: AsyncSession
    ) -> None:
        participant = await self.check_participant_by_id(
            participant_id=participant_id, session=session
        )
        await session.execute(
            update(ParticipantModel)
            .where(ParticipantModel.id == participant.id)
            .values(bet=bet)
        )
        await session.execute(
            update(PlayerModel)
            .where(PlayerModel.id == participant.player.id)
            .values(balance=participant.player.balance - bet)
        )

    async def is_participants_gathered(
        self, chat_id: int, session: AsyncSession
    ) -> bool:
        game_session = await self.check_game_session(
            chat_id=chat_id, session=session
        )
        expected_users_num = game_session.num_users
        num_participants = await session.scalar(func.count(GameSessionModel.id))
        return expected_users_num == num_participants

    async def set_participant_cards(
        self, participant_id: int, cards: Cards, session: AsyncSession
    ) -> None:
        await self.check_participant_by_id(
            participant_id=participant_id, session=session
        )
        await session.execute(
            update(ParticipantModel)
            .where(ParticipantModel.id == participant_id)
            .values(right_hand=cards.to_dict(cards))
        )

    async def get_participant_cards(
        self, participant_id: int, session: AsyncSession
    ) -> Cards:
        participant = await self.check_participant_by_id(
            participant_id=participant_id, session=session
        )
        return Cards.from_dict(participant.right_hand)
