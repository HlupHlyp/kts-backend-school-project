from sqlalchemy import select, update
from app.blackjack.models import GameSessionStatus, ParticipantStatus

from app.base.base_accessor import BaseAccessor
from app.blackjack.models import (
    GameSessionModel,
    GameSessionStatus,
    ParticipantModel,
    ParticipantStatus,
    PlayerModel,
)
from app.store.bot.dataclasses import Cards
from sqlalchemy.ext.asyncio import AsyncSession

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
            select(GameSessionModel).where(GameSessionModel.chat_id == chat_id)
        )

    async def check_game_session(
        self, session: AsyncSession, chat_id: int
    ) -> GameSessionModel:
        game_session = await self.get_game_session_by_chat(
            chat_id=chat_id, session=session
        )
        if game_session is None:
            raise Exception(f"Сессия для чата '{chat_id}' не найдена")

    async def set_game_session_users_num(
        self, session: AsyncSession, chat_id: int, users_num: int
    ) -> None:
        self.check_game_session(chat_id=chat_id, session=session)
        await session.execute(
            update(GameSessionModel)
            .where(GameSessionModel.chat_id == chat_id)
            .values(num_users=users_num)
        )

    async def set_game_session_status(
        self, session: AsyncSession, chat_id: int, status: GameSessionStatus
    ) -> None:
        self.check_game_session(chat_id=chat_id, session=session)
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
            raise Exception(f"Игрок c tg_id:'{tg_id}' не участвует в сессии")

    async def get_participant_by_tg_and_chat_id(
        self, tg_id: int, chat_id: int, session: AsyncSession
    ) -> ParticipantModel | None:
        player = await self.check_player(tg_id=tg_id, session=session)
        game_session = await self.check_game_session(chat_id, session=session)
        return await session.scalar(
            select(ParticipantModel).where(
                ParticipantModel.player_id == player.id,
                ParticipantModel.game_session_id == game_session.chat_id,
            )
        )

    async def get_or_create_participant(
        self, tg_id: int, chat_id: int, session: AsyncSession
    ) -> ParticipantModel | None:
        participant = await self.get_participant_by_tg_and_chat_id(
            sessions=session, tg_id=tg_id, chat_id=chat_id
        )
        if participant is None:
            player = await self.check_player(tg_id=tg_id, session=session)
            game_session = await self.check_game_session(
                chat_id, session=session
            )
            participant = ParticipantModel(
                game_session_id=game_session.id,
                player_id=player.id,
                status=ParticipantStatus.sleeping,
            )
            session.add(participant)
        return participant

    async def get_participant_by_id(
        self, participant_id: int, session: AsyncSession
    ) -> ParticipantModel | None:
        return await session.scalar(
            select(ParticipantModel)
            .where(ParticipantModel.id == participant_id)
            .options
        )

    async def check_participant_by_id(
        self, participant_id: int, session: AsyncSession
    ) -> ParticipantModel:
        participant = await session.scalar(
            select(ParticipantModel).where(
                ParticipantModel.id == participant_id
            )
        )
        if participant is None:
            raise Exception(f"Участник c id:'{participant_id}' не существует")
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
        game_session = await self.check_game_session(chat_id, session=session)
        expected_users_num = game_session.num_users
        participants = await session.execute(
            select(ParticipantModel).where(
                ParticipantModel.game_session_id == game_session.id
                and ParticipantModel.status == ParticipantStatus.ACTIVE
            )
        )
        return expected_users_num == len(list(participants))

    async def set_participant_cards(
        self, participant_id: int, cards: Cards, session: AsyncSession
    ) -> None:
        await self.check_participant_by_id(
            participant_id=participant_id, session=session
        )
        await session.execute(
            update(ParticipantModel)
            .where(ParticipantModel.id == participant_id)
            .values(right_hand=Cards.Schema().dump(cards))
        )

    async def get_participant_cards(
        self, participant_id: int, session: AsyncSession
    ) -> Cards:
        participant = await self.check_participant_by_id(
            participant_id=participant_id, session=session
        )
        if participant is None:
            raise Exception(f"Участник c id:'{participant_id}' не найден")
        return Cards.Schema().load(participant.right_hand)
