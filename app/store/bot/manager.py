import json
import os
import typing
from logging import getLogger

import aiohttp

from app.store.bot.dataclasses import Markup, ReplyTemplates
from app.store.bot.router import BotRouter
from app.store.tg_api.dataclasses import SendMessageResponse, UpdateObj

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
        self.reply_templates = ReplyTemplates.Schema().load(
            self.reply_templates
        )
        self.router = BotRouter(self)
        self.router.create_route(
            trigger="start@SC17854_bot", is_command=True, func=start_handler
        )
        self.router.create_route(
            trigger="stop@SC17854_bot", is_command=True, func=stop_handler
        )
        self.router.create_route(
            trigger="num_players", is_command=False, func=players_num_handler
        )

    async def send_message(
        self, chat_id: int, text: str, markup: dict | None
    ) -> SendMessageResponse:
        url = self.app.store.tg_api.get_url("sendMessage")
        payload = {"chat_id": chat_id, "text": text, "reply_markup": markup}
        async with aiohttp.ClientSession() as session:
            async with session.post(url, json=payload) as resp:
                res_dict = await resp.json()
                return SendMessageResponse.Schema().load(res_dict)
        return self.app.store.tg_api.tg_client.send_message

    @property
    def blackjack(self):
        return self.app.store.blackjack

    async def send_reply(self, reply_name: str, chat_id: int) -> None:
        reply_template = next(
            filter(
                lambda reply: reply.name == reply_name,
                self.reply_templates.data,
            )
        )
        await self.send_message(
            chat_id=chat_id,
            text=reply_template.content.text,
            markup=Markup.Schema().dump(
                reply_template.content.markup,
            ),
        )

    async def handle_updates(self, updates: list[UpdateObj]) -> None:
        for update in updates.result:
            await self.router.navigate(update)
