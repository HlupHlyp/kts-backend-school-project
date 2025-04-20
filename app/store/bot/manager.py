import json
import os
import typing
from logging import getLogger

import aiohttp

from app.store.bot.dataclasses import Markup, ReplyTemplates
from app.store.bot.handlers import (
    bet_handler,
    players_num_handler,
    start_handler,
    stop_handler,
)
from app.store.bot.router import BotRouter
from app.store.tg_api.dataclasses import SendMessageResponse, UpdateObj

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
        self.reply_templates = ReplyTemplates.Schema().load(
            self.reply_templates
        )
        self.router = BotRouter(self)
        self.router.create_route(
            route_str="start@SC17854_bot", func=start_handler
        )
        self.router.create_route(
            route_str="stop@SC17854_bot", func=stop_handler
        )
        self.router.create_route(
            route_str="num_players", func=players_num_handler
        )
        self.router.create_route(route_str="make_a_bet", func=bet_handler)

    async def send_message(
        self,
        chat_id: int,
        text: str,
        markup: dict | None = None,
    ) -> SendMessageResponse | None:
        url, payload = self.app.store.tg_api.get_url("sendMessage"), None
        if markup:
            payload = {"chat_id": chat_id, "text": text, "reply_markup": markup}
        else:
            payload = {
                "chat_id": chat_id,
                "text": text,
                "reply_markup": {"inline_keyboard": [[]]},
            }
        async with self.session.post(url, json=payload) as resp:
            res_dict = await resp.json()
            return SendMessageResponse.Schema().load(res_dict)
        return None

    @property
    def blackjack(self):
        return self.app.store.blackjack

    async def send_reply(self, reply_name: str, chat_id: int) -> None:
        reply_template = next(
            reply
            for reply in self.reply_templates.data
            if reply.name == reply_name
        )
        if reply_template is None:
            raise Exception(
                f"reply_template with name: {reply_name} hasn't been found"
            )
        await self.send_message(
            chat_id=chat_id,
            text=reply_template.content.text,
            markup=Markup.Schema().dump(
                reply_template.content.markup,
            ),
        )

    async def handle_updates(
        self, session: aiohttp.ClientSession, updates: list[UpdateObj]
    ) -> None:
        self.session = session
        for update in updates.result:
            await self.router.navigate(update)
