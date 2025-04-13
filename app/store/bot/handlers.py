import typing

from app.store.tg_api.dataclasses import UpdateObj

if typing.TYPE_CHECKING:
    from app.store.bot.manager import BotManager


async def start_handler(
    manager: "BotManager", update: UpdateObj, params: list | None = None
):
    reply_dict_key = ""
    chat_id = update.message.chat.id
    g_session = await manager.blackjack.create_g_session(chat_id)
    if g_session.status != "sleeping":
        reply_dict_key = "session_already_started"
    else:
        reply_dict_key = "player_num_setting"
    await manager.send_reply(chat_id=chat_id, reply_dict_key=reply_dict_key)


async def stop_handler(
    manager: "BotManager", update: UpdateObj, params: list | None = None
):
    chat_id = update.message.chat.id
    reply_dict_key = "stopping_game"
    await manager.send_reply(chat_id=chat_id, reply_dict_key=reply_dict_key)


async def players_num_handler(
    manager: "BotManager", update: UpdateObj, params: list | None = None
):
    chat_id = update.callback_query.message.chat.id
    reply_dict_key = "inviting"
    await manager.send_reply(chat_id=chat_id, reply_dict_key=reply_dict_key)
