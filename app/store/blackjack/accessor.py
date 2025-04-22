from sqlalchemy import func, select, update
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import joinedload, selectinload

from app.base.base_accessor import BaseAccessor
from app.blackjack.models import (
    GameSessionModel,
    GameSessionStatus,
    ParticipantModel,
    ParticipantStatus,
    PlayerModel,
)
from app.store.bot.dataclasses import Cards
from app.store.bot.exceptions import (
    GameSessionNotFoundError,
    ParticipantNotFoundError,
    PlayerNotFoundError,
)

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
        return await self.get_game_session_for_update(
            chat_id=chat_id, session=session
        )

    async def get_game_session_by_chat(
        self,
        session: AsyncSession,
        chat_id: int,
    ) -> GameSessionModel | None:
        return await session.scalar(
            select(GameSessionModel)
            .where(GameSessionModel.chat_id == chat_id)
            .options(joinedload(GameSessionModel.participants))
        )

    async def get_game_session_for_update(
        self,
        session: AsyncSession,
        chat_id: int,
    ) -> GameSessionModel:
        result = await session.scalar(
            select(GameSessionModel)
            .where(GameSessionModel.chat_id == chat_id)
            .with_for_update()
        )
        if result is None:
            raise GameSessionNotFoundError
        return result

    async def set_game_session_users_num(
        self,
        session: AsyncSession,
        game_session: GameSessionModel,
        users_num: int,
    ) -> None:
        await session.execute(
            update(GameSessionModel)
            .where(GameSessionModel.id == game_session.id)
            .values(num_users=users_num)
        )

    async def set_game_session_status(
        self,
        session: AsyncSession,
        game_session: GameSessionModel,
        status: GameSessionStatus,
    ) -> None:
        result = await session.execute(
            update(GameSessionModel)
            .where(GameSessionModel.id == game_session.id)
            .values(status=status)
        )
        if result.rowcount == 0:
            raise GameSessionNotFoundError

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

    async def get_participant_by_tg_and_chat_id(
        self, tg_id: int, chat_id: int, session: AsyncSession
    ) -> ParticipantModel | None:
        player = await self.get_player_by_tg_id(tg_id=tg_id, session=session)
        if player is None:
            return None
        game_session = await self.get_game_session_by_chat(
            chat_id=chat_id, session=session
        )
        if game_session is None:
            raise GameSessionNotFoundError
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
            game_session = await self.get_game_session_by_chat(
                chat_id=chat_id, session=session
            )
            if game_session is None:
                raise GameSessionNotFoundError
            participant = ParticipantModel(
                game_session_id=game_session.id,
                player_id=player.id,
                status=ParticipantStatus.SLEEPING,
            )
            session.add(participant)
            await session.commit()
        return await self.get_participant_for_update(
            session=session, tg_id=tg_id, chat_id=chat_id
        )

    async def get_participants_for_update(
        self,
        session: AsyncSession,
        game_session: GameSessionModel,
    ) -> list[ParticipantModel]:
        result = await session.scalars(
            select(ParticipantModel)
            .where(ParticipantModel.game_session_id == game_session.id)
            .options(selectinload(ParticipantModel.player))
        )
        if result is None:
            raise GameSessionNotFoundError
        return result

    async def set_participant_status(
        self,
        participant: ParticipantModel,
        status: ParticipantStatus,
        session: AsyncSession,
    ) -> None:
        result = await session.execute(
            update(ParticipantModel)
            .where(ParticipantModel.id == participant.id)
            .values(status=status)
        )
        if result.rowcount == 0:
            raise ParticipantNotFoundError

    async def get_participant_for_update(
        self, chat_id: int, tg_id: int, session: AsyncSession
    ) -> ParticipantModel:
        player = await self.get_player_by_tg_id(tg_id=tg_id, session=session)
        if player is None:
            raise PlayerNotFoundError
        game_session = await self.get_game_session_by_chat(
            chat_id=chat_id, session=session
        )
        if game_session is None:
            raise GameSessionNotFoundError
        result = await session.scalar(
            select(ParticipantModel)
            .where(
                ParticipantModel.player_id == player.id,
                ParticipantModel.game_session_id == game_session.id,
            )
            .options(selectinload(ParticipantModel.player))
            .with_for_update()
        )
        if result is None:
            raise ParticipantNotFoundError
        return result

    async def set_participant_bet(
        self, participant: ParticipantModel, bet: int, session: AsyncSession
    ) -> None:
        result = await session.execute(
            update(ParticipantModel)
            .where(ParticipantModel.id == participant.id)
            .values(bet=bet)
        )
        if result.rowcount == 0:
            raise ParticipantNotFoundError
        result = await session.execute(
            update(PlayerModel)
            .where(PlayerModel.id == participant.player.id)
            .values(balance=participant.player.balance - bet)
        )
        if result.rowcount == 0:
            raise PlayerNotFoundError

    async def is_participants_gathered(
        self, game_session: GameSessionModel, session: AsyncSession
    ) -> bool:
        expected_users_num = game_session.num_users
        num_participants = await session.scalar(
            select(func.count(ParticipantModel.id)).where(
                ParticipantModel.game_session_id == game_session.id,
                ParticipantModel.status == ParticipantStatus.ACTIVE,
            )
        )
        return expected_users_num == num_participants

    async def set_participant_cards(
        self, participant: ParticipantModel, cards: Cards, session: AsyncSession
    ) -> None:
        result = await session.execute(
            update(ParticipantModel)
            .where(ParticipantModel.id == participant.id)
            .values(right_hand=cards.to_dict())
        )
        if result.rowcount == 0:
            raise ParticipantNotFoundError

    async def set_dealer_cards(
        self,
        game_session: GameSessionModel,
        cards: Cards,
        session: AsyncSession,
    ) -> None:
        await session.execute(
            update(GameSessionModel)
            .where(GameSessionModel.id == game_session.id)
            .values(dealer_cards=cards.to_dict())
        )

    async def switch_poll_participant(
        self, game_session: GameSessionStatus, session: AsyncSession
    ) -> ParticipantModel:
        participants = await self.get_participants_for_update(
            session=session, game_session=game_session
        )
        new_poll_participant = next(
            participant
            for participant in participants
            if participant.status == ParticipantStatus.ACTIVE
        )
        if new_poll_participant is None:
            raise Exception
        await self.set_participant_status(
            participant=new_poll_participant,
            status=ParticipantStatus.POLLING,
            session=session,
        )
        return new_poll_participant
