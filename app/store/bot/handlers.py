import typing

from app.blackjack.models import GameSessionStatus, ParticipantStatus
from app.store.tg_api.dataclasses import UpdateObj

if typing.TYPE_CHECKING:
    from app.store.bot.manager import BotManager


async def start_handler(
    manager: "BotManager", update: UpdateObj, params: list | None = None
) -> None:
    reply_name = ""
    chat_id = update.message.chat.id
    game_session = await manager.blackjack.create_game_session(chat_id)
    if game_session.status != GameSessionStatus.sleeping:
        reply_name = "session_already_started"
    else:
        reply_name = "player_num_setting"
        await manager.blackjack.set_game_session_status(
            chat_id=chat_id, status=GameSessionStatus.waiting_for_num
        )
    await manager.send_reply(chat_id=chat_id, reply_name=reply_name)


async def stop_handler(
    manager: "BotManager", update: UpdateObj, params: list | None = None
) -> None:
    chat_id = update.message.chat.id

    reply_name = "stopping_game"
    await manager.send_reply(chat_id=chat_id, reply_name=reply_name)


async def players_num_handler(
    manager: "BotManager", update: UpdateObj, params: list | None = None
) -> None:
    chat_id = update.callback_query.message.chat.id
    reply_name = "inviting"
    game_session = await manager.blackjack.create_game_session(chat_id)
    if game_session.status == GameSessionStatus.waiting_for_num:
        await manager.blackjack.set_game_session_users_num(
            chat_id=chat_id, users_num=int(params[0])
        )
        await manager.blackjack.set_game_session_status(
            chat_id=chat_id, status=GameSessionStatus.waiting_for_users
        )
        await manager.send_message(
            chat_id=chat_id, text=f"Число участников: {params[0]}"
        )
        await manager.send_reply(chat_id=chat_id, reply_name=reply_name)


async def bet_handler(
    manager: "BotManager", update: UpdateObj, params: list | None = None
) -> None:
    chat_id = update.callback_query.message.chat.id
    tg_id = update.callback_query.from_.id
    username = update.callback_query.from_.username

    player = await manager.blackjack.get_player_by_tg_id(tg_id=tg_id)
    if player is None:
        player = await manager.blackjack.create_player(
            tg_id=tg_id, username=username
        )
    participant = await manager.blackjack.get_participant_by_tg_and_chat_id(
        tg_id=tg_id, chat_id=chat_id
    )
    if participant is None:
        participant = await manager.blackjack.create_participant(
            tg_id=tg_id, chat_id=chat_id
        )
    if participant.status == ParticipantStatus.sleeping:
        await manager.blackjack.set_participant_bet(
            tg_id=tg_id, chat_id=chat_id, bet=int(params[0])
        )
        await manager.blackjack.set_participant_status(
            tg_id=tg_id, chat_id=chat_id, status=ParticipantStatus.active
        )
        await manager.send_message(
            chat_id=chat_id,
            text=f" {player.username} поставил: {params[0]}🟡",
        )
    enough_gathered = await manager.blackjack.is_participants_gathered(
        chat_id=chat_id
    )

    if enough_gathered:
        await manager.blackjack.set_game_session_status(
            chat_id=chat_id, status=GameSessionStatus.polling
        )
