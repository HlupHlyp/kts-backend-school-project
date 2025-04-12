import json
import os
import typing
from logging import getLogger

from app.store.tg_api.dataclasses import UpdateObj

if typing.TYPE_CHECKING:
    from app.web.app import Application


class BotManager:
    def __init__(self, app: "Application"):
        self.app = app
        self.bot = None
        self.logger = getLogger("handler")
        path = os.path.join(
            os.path.dirname(os.path.realpath(__file__)), "reply_templates.json"
        )
        with open(path, "r") as file:
            self.reply_templates = json.load(file)

    @property
    def tg_client(self):
        return self.app.store.Tg_api.tg_client

    async def handle_updates(self, updates: list[UpdateObj]):
        for update in updates.result:
            reply = False
            reply_dict_key = ""
            if update.message is not None:
                chat_id = update.message.chat.id
                if update.message.text == "/start@SC17854_bot":
                    g_session = await self.app.store.blackjack.create_g_session(
                        chat_id
                    )
                    if g_session.status != "sleeping":
                        reply_dict_key = True, "session_already_started"
                    else:
                        reply, reply_dict_key = True, "player_num_setting"

                elif update.message.text == "/stop@SC17854_bot":
                    reply = True
                    reply_dict_key = "stopping_game"

            elif update.callback_query is not None:
                if "num_players" in update.callback_query.data:
                    chat_id = update.callback_query.message.chat.id
                    reply = True
                    reply_dict_key = "inviting"

            if reply:
                reply_template = self.reply_templates[reply_dict_key]
                await self.tg_client.send_message(
                    chat_id=chat_id,
                    text=reply_template["text"],
                    markup=reply_template["markup"],
                )
