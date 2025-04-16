import typing

from app.store.tg_api.dataclasses import UpdateObj

if typing.TYPE_CHECKING:
    from app.store.bot.manager import BotManager


async def start_handler(
    manager: "BotManager", update: UpdateObj, params: list | None = None
) -> None:
    reply_name = ""
    chat_id = update.message.chat.id
    game_session = await manager.blackjack.create_game_session(chat_id)
    if game_session.status != "sleeping":
        reply_name = "session_already_started"
    else:
        reply_name = "player_num_setting"
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
    await manager.send_reply(chat_id=chat_id, reply_name=reply_name)
