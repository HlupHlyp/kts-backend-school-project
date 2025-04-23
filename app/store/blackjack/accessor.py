from sqlalchemy import desc, func, select, update
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
    NoActiveParticipantsError,
    ParticipantNotFoundError,
    PlayerNotFoundError,
)

DEFAULT_BALANCE = 10000
DEFAULT_PLAYERS_NUM = 10000


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
        num_users: int,
    ) -> None:
        await session.execute(
            update(GameSessionModel)
            .where(GameSessionModel.id == game_session.id)
            .values(num_users=num_users)
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
        self, session: AsyncSession, tg_id: int, username: str
    ) -> None:
        player = await self.get_player_by_tg_id(tg_id=tg_id, session=session)
        if player is None:
            player = PlayerModel(
                tg_id=tg_id, username=username, balance=DEFAULT_BALANCE
            )
            session.add(player)
        return player

    async def get_participant_by_tg_and_chat_id(
        self, session: AsyncSession, tg_id: int, chat_id: int
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
        self, session: AsyncSession, tg_id: int, username: str, chat_id: int
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
            .where(
                ParticipantModel.game_session_id == game_session.id,
                ParticipantModel.status != ParticipantStatus.SLEEPING,
            )
            .options(joinedload(ParticipantModel.player))
            .with_for_update(of=ParticipantModel)
        )
        if result is None:
            raise GameSessionNotFoundError
        return result

    async def set_participant_status(
        self,
        session: AsyncSession,
        participant: ParticipantModel,
        status: ParticipantStatus,
    ) -> None:
        result = await session.execute(
            update(ParticipantModel)
            .where(ParticipantModel.id == participant.id)
            .values(status=status)
        )
        if result.rowcount == 0:
            raise ParticipantNotFoundError

    async def get_participant_for_update(
        self, session: AsyncSession, chat_id: int, tg_id: int
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
            .with_for_update(of=ParticipantModel)
        )
        if result is None:
            raise ParticipantNotFoundError
        return result

    async def set_participant_bet(
        self, session: AsyncSession, participant: ParticipantModel, bet: int
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
        self,
        session: AsyncSession,
        game_session: GameSessionModel,
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
        self, session: AsyncSession, participant: ParticipantModel, cards: Cards
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
        self, session: AsyncSession, game_session: GameSessionStatus
    ) -> ParticipantModel:
        participants = await self.get_participants_for_update(
            session=session, game_session=game_session
        )
        try:
            new_poll_participant = next(
                participant
                for participant in participants
                if participant.status == ParticipantStatus.ACTIVE
            )
        except StopIteration as e:
            raise NoActiveParticipantsError from e
        else:
            await self.set_participant_status(
                participant=new_poll_participant,
                status=ParticipantStatus.POLLING,
                session=session,
            )
            return new_poll_participant

    async def change_balance_on_bet_amount(
        self, session: AsyncSession, participant: ParticipantModel, coef: int
    ) -> None:
        result = await session.execute(
            update(PlayerModel)
            .where(PlayerModel.id == participant.player.id)
            .values(balance=PlayerModel.balance + participant.bet * coef)
        )
        if result.rowcount == 0:
            raise PlayerNotFoundError(participant.player.tg_id)

    async def top_up_balance(self, username: str, amount: int) -> None:
        async with self.app.database.session() as session:
            result = await session.execute(
                update(PlayerModel)
                .where(PlayerModel.username == username)
                .values(balance=PlayerModel.balance + amount)
            )
            if result.rowcount == 0:
                raise PlayerNotFoundError(None)

    async def get_money_rating(
        self,
        chat_id: int | None = None,
        num_players: int | None = DEFAULT_PLAYERS_NUM,
    ) -> list[PlayerModel]:
        """Акксессор для извлечения всех пользователей или по чату.
        Назван по View, для которого написан
        """
        async with self.app.database.session() as session:
            if chat_id is None:
                return await session.scalars(
                    select(PlayerModel)
                    .order_by(desc(PlayerModel.balance))
                    .limit(num_players)
                )
            game_session = await self.get_game_session_by_chat(
                session=session, chat_id=chat_id
            )
            if game_session is None:
                raise GameSessionNotFoundError(chat_id)
            return await session.scalars(
                select(PlayerModel).where(
                    select(1)
                    .select_from(ParticipantModel)
                    .where(
                        ParticipantModel.player_id == PlayerModel.id,
                        ParticipantModel.game_session_id == game_session.id,
                    )
                    .exists()
                    .order_by(desc(PlayerModel.balance))
                    .limit(num_players)
                )
            )
