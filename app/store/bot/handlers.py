import enum
import typing

from app.blackjack.models import GameSessionStatus, ParticipantStatus
from app.store.tg_api.dataclasses import UpdateObj

if typing.TYPE_CHECKING:
    from app.store.bot.manager import BotManager


class ReplyTemplates(enum.StrEnum):
    PLAYER_NUM_SETTING = "PLAYER_NUM_SETTING"
    INVITING = "INVITING"
    STARTING_GAME = "STARTING_GAME"
    STOPPING_GAME = "STOPPING_GAME"
    SESSION_ALREADY_STARTED = "SESSION_ALREADY_STARTED"


async def start_handler(
    manager: "BotManager", update: UpdateObj | None = None
) -> None:
    chat_id = update.chat_id
    async with manager.app.database.session() as session:
        game_session = await manager.blackjack.get_or_create_game_session(
            chat_id=chat_id, session=session
        )
        if game_session.status != GameSessionStatus.SLEEPING:
            await manager.send_reply(
                chat_id=chat_id,
                reply_name=ReplyTemplates.SESSION_ALREADY_STARTED,
            )
        else:
            await manager.blackjack.set_game_session_status(
                chat_id=chat_id,
                status=GameSessionStatus.WAITING_FOR_NUM,
                session=session,
            )
            await manager.send_reply(
                chat_id=chat_id, reply_name=ReplyTemplates.PLAYER_NUM_SETTING
            )
        await session.commit()


async def stop_handler(
    manager: "BotManager", update: UpdateObj | None = None
) -> None:
    chat_id = update.chat_id
    reply_name = ReplyTemplates.STOPPING_GAME
    await manager.send_reply(chat_id=chat_id, reply_name=reply_name)


async def players_num_handler(manager: "BotManager", update: UpdateObj) -> None:
    chat_id = update.chat_id
    users_num = int(update.callback_query.data.split("/")[1])
    reply_name = ReplyTemplates.INVITING
    async with manager.app.database.session() as session:
        game_session = await manager.blackjack.get_game_session_for_update(
            chat_id=chat_id, session=session
        )
        if game_session.status == GameSessionStatus.WAITING_FOR_NUM:
            await manager.blackjack.set_game_session_users_num(
                chat_id=chat_id, users_num=users_num, session=session
            )
            await manager.blackjack.set_game_session_status(
                chat_id=chat_id,
                status=GameSessionStatus.WAITING_FOR_USERS,
                session=session,
            )
            await manager.send_message(
                chat_id=chat_id, text=f"Число участников: {users_num}"
            )
            await manager.send_reply(chat_id=chat_id, reply_name=reply_name)
        await session.commit()


async def bet_handler(manager: "BotManager", update: UpdateObj) -> None:
    chat_id = update.chat_id
    tg_id = update.tg_id
    username = update.username
    bet = int(update.callback_query.data.split("/")[1])
    async with manager.app.database.session() as session:
        participant = await manager.blackjack.get_or_create_participant(
            tg_id=tg_id, chat_id=chat_id, username=username, session=session
        )
        if participant.status == ParticipantStatus.SLEEPING:
            await manager.blackjack.set_participant_bet(
                participant=participant, bet=int(bet), session=session
            )
            await manager.blackjack.set_participant_status(
                participant=participant,
                status=ParticipantStatus.ACTIVE,
                session=session,
            )
            await manager.send_message(
                chat_id=chat_id,
                text=f" {participant.player.username} поставил: {bet}🟡",
            )
            await session.commit()
            game_session = manager.blackjack.get_game_session_for_update(
                chat_id=chat_id, session=session
            )
            enough_gathered = await manager.blackjack.is_participants_gathered(
                game_session=game_session, session=session
            )
            if enough_gathered:
                await manager.blackjack.set_game_session_status(
                    chat_id=chat_id, status=GameSessionStatus.POLLING
                )
            await session.commit()
