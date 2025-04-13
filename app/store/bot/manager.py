import json
import os
import typing
from logging import getLogger

from app.store.bot.router import BotRouter
from app.store.tg_api.dataclasses import UpdateObj

if typing.TYPE_CHECKING:
    from app.web.app import Application

from app.store.bot.handlers import (
    players_num_handler,
    start_handler,
    stop_handler,
)


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
        self.router = BotRouter(self)
        self.router.create_route(
            trigger="start@SC17854_bot", is_command=True, action=start_handler
        )
        self.router.create_route(
            trigger="stop@SC17854_bot", is_command=True, action=stop_handler
        )
        self.router.create_route(
            trigger="num_players", is_command=False, action=players_num_handler
        )

    @property
    def send_message(self):
        return self.app.store.Tg_api.tg_client.send_message

    @property
    def blackjack(self):
        return self.app.store.blackjack

    async def send_reply(self, reply_dict_key: dict, chat_id):
        reply_template = self.reply_templates[reply_dict_key]
        await self.send_message(
            chat_id=chat_id,
            text=reply_template["text"],
            markup=reply_template["markup"],
        )

    async def handle_updates(self, updates: list[UpdateObj]):
        for update in updates.result:
            await self.router.navigate(update)
