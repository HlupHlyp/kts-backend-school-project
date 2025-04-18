from sqlalchemy import select, update

from app.base.base_accessor import BaseAccessor
from app.blackjack.models import (
    GameSessionModel,
    GameSessionStatus,
    ParticipantModel,
    ParticipantStatus,
    PlayerModel,
)
from app.store.bot.dataclasses import Cards

DEFAULT_BALANCE = 10000


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

    async def get_player_by_tg_id(self, tg_id: int) -> PlayerModel:
        async with self.app.database.session() as session:
            return await session.scalar(
                select(PlayerModel).where(PlayerModel.tg_id == tg_id)
            )

    async def create_player(self, tg_id: int, username: str) -> None:
        player = await self.get_player_by_tg_id(tg_id=tg_id)
        if player is None:
            player = PlayerModel(
                tg_id=tg_id, username=username, balance=DEFAULT_BALANCE
            )
            async with self.app.database.session() as session:
                session.add(player)
                await session.commit()
        return player

    async def get_participant_by_tg_and_chat_id(
        self, tg_id: int, chat_id: int
    ) -> ParticipantModel | None:
        async with self.app.database.session() as session:
            player = await self.get_player_by_tg_id(tg_id=tg_id)
            game_session = await self.get_game_session_by_chat(chat_id)
            if game_session and player:
                return await session.scalar(
                    select(ParticipantModel).where(
                        ParticipantModel.player_id == player.id
                        and ParticipantModel.game_session_id
                        == game_session.chat_id
                    )
                )
            return None

    async def create_participant(
        self, tg_id: int, chat_id: int
    ) -> ParticipantModel | None:
        participant = await self.get_participant_by_tg_and_chat_id(
            tg_id=tg_id, chat_id=chat_id
        )
        if participant is None:
            player = await self.get_player_by_tg_id(tg_id=tg_id)
            game_session = await self.get_game_session_by_chat(chat_id)
            participant = ParticipantModel(
                game_session_id=game_session.id,
                player_id=player.id,
                status=ParticipantStatus.sleeping,
            )
            async with self.app.database.session() as session:
                session.add(participant)
                await session.commit()
        return participant

    async def set_participant_status(
        self, tg_id: int, chat_id: int, status: ParticipantStatus
    ) -> None:
        participant = await self.get_participant_by_tg_and_chat_id(
            tg_id=tg_id, chat_id=chat_id
        )
        if participant is not None:
            async with self.app.database.session() as session:
                await session.execute(
                    update(ParticipantModel)
                    .where(ParticipantModel.id == participant.id)
                    .values(status=status)
                )
                await session.commit()

    async def set_participant_bet(
        self, tg_id: int, chat_id: int, bet: int
    ) -> None:
        player = await self.get_player_by_tg_id(tg_id=tg_id)
        participant = await self.get_participant_by_tg_and_chat_id(
            tg_id=tg_id, chat_id=chat_id
        )
        if participant is not None:
            async with self.app.database.session() as session:
                await session.execute(
                    update(ParticipantModel)
                    .where(ParticipantModel.id == participant.id)
                    .values(bet=bet)
                )
                await session.execute(
                    update(PlayerModel)
                    .where(PlayerModel.id == player.id)
                    .values(balance=player.balance - bet)
                )
                await session.commit()

    async def is_participants_gathered(self, chat_id: int) -> bool:
        game_session = await self.get_game_session_by_chat(chat_id)
        expected_users_num = game_session.num_users
        async with self.app.database.session() as session:
            participants = await session.execute(
                select(ParticipantModel).where(
                    ParticipantModel.game_session_id == game_session.id
                    and ParticipantModel.status == ParticipantStatus.active
                )
            )
            return expected_users_num == len(list(participants))

    async def set_participant_cards(
        self, participant_id: int, cards: Cards
    ) -> None:
        async with self.app.database.session() as session:
            await session.execute(
                update(ParticipantModel)
                .where(ParticipantModel.id == participant_id)
                .values(right_hand=Cards.Schema().dump(cards))
            )
            await session.commit()

    async def get_participant_cards(self, participant_id: int) -> Cards | None:
        async with self.app.database.session() as session:
            participant = await session.scalar(
                select(ParticipantModel).where(
                    ParticipantModel.id == participant_id
                )
            )
            if participant.right_hand is not None:
                return Cards.Schema().load(participant.right_hand)
        return None
