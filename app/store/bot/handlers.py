import typing

from app.store.tg_api.dataclasses import UpdateObj
from app.blackjack.models import GameSessionStatus

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
    print(reply_name)
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
        print("!!!" * 2)
        await manager.blackjack.set_game_session_status(
            chat_id=chat_id, status=GameSessionStatus.waiting_for_users
        )
        await manager.send_message(
            chat_id=chat_id, text=f"Число участников: {params[0]}"
        )
        await manager.send_reply(chat_id=chat_id, reply_name=reply_name)
