import typing

from app.blackjack.models import GameSessionStatus, ParticipantStatus
from app.store.tg_api.dataclasses import UpdateObj

if typing.TYPE_CHECKING:
    from app.store.bot.manager import BotManager


async def start_handler(
    manager: "BotManager", update: UpdateObj | None = None
) -> None:
    chat_id = update.message.chat.id
    async with manager.app.database.session() as session:
        game_session = await manager.blackjack.get_or_create_game_session(
            chat_id, session=session
        )
        if game_session.status != GameSessionStatus.SLEEPING:
            await manager.send_reply(
                chat_id=chat_id, reply_name="session_already_started"
            )
        else:
            await manager.blackjack.set_game_session_status(
                chat_id=chat_id,
                status=GameSessionStatus.WAITING_FOR_NUM,
                session=session,
            )
            await session.commit()
            await manager.send_reply(
                chat_id=chat_id, reply_name="player_num_setting"
            )


async def stop_handler(
    manager: "BotManager", update: UpdateObj | None = None
) -> None:
    chat_id = update.message.chat.id
    reply_name = "stopping_game"
    await manager.send_reply(chat_id=chat_id, reply_name=reply_name)


async def players_num_handler(
    manager: "BotManager", update: UpdateObj, params: list | None = None
) -> None:
    chat_id = update.callback_query.message.chat.id
    users_num = str(update.callback_query.data).split("/")[1]
    reply_name = "inviting"
    async with manager.app.database.session() as session:
        game_session = await manager.blackjack.get_or_create_game_session(
            chat_id, session=session
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
            await session.commit()
            await manager.send_message(
                chat_id=chat_id, text=f"Число участников: {users_num}"
            )
            await manager.send_reply(chat_id=chat_id, reply_name=reply_name)


async def bet_handler(
    manager: "BotManager", update: UpdateObj, params: list | None = None
) -> None:
    chat_id = update.callback_query.message.chat.id
    tg_id = update.callback_query.from_.id
    username = update.callback_query.from_.username
    bet = str(update.callback_query.data).split("/")[1]
    async with manager.app.database.session() as session:
        player = await manager.blackjack.get_or_create_player(
            tg_id=tg_id, username=username, session=session
        )
        participant = await manager.blackjack.get_or_create_participant(
            tg_id=tg_id, chat_id=chat_id, session=session
        )
        if participant.status == ParticipantStatus.SLEEPING:
            await manager.blackjack.set_participant_bet(
                tg_id=tg_id, chat_id=chat_id, bet=int(bet)
            )
            await manager.blackjack.set_participant_status(
                tg_id=tg_id, chat_id=chat_id, status=ParticipantStatus.ACTIVE
            )
            await session.commit()
            await manager.send_message(
                chat_id=chat_id,
                text=f" {player.username} поставил: {bet}🟡",
            )
        enough_gathered = await manager.blackjack.is_participants_gathered(
            chat_id=chat_id
        )
        if enough_gathered:
            await manager.blackjack.set_game_session_status(
                chat_id=chat_id, status=GameSessionStatus.POLLING
            )
            await session.commit()
