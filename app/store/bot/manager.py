import asyncio
import json
import os
import typing
from logging import getLogger

import aiohttp

from app.base.base_accessor import BaseAccessor
from app.store.bot.dataclasses import Markup, ReplyTemplates
from app.store.bot.exceptions import ReplyTemplateNotFoundError
from app.store.bot.handlers import (
    bet_handler,
    enough_handler,
    get_card_handler,
    players_num_handler,
    start_handler,
    stop_handler,
    get_balances_handler,
    get_prev_session_handler,
    get_rules_handler,
)
from app.store.bot.router import BotRouter, Command, Query
from app.store.tg_api.dataclasses import SendMessageResponse

if typing.TYPE_CHECKING:
    from app.web.app import Application

NUM_WORKERS = 3


class BotManager(BaseAccessor):
    def __init__(self, app: "Application", *args, **kwargs):
        super().__init__(app, *args, **kwargs)
        self.app = app
        self.bot = None
        self.logger = getLogger("handler")
        path = os.path.join(
            os.path.dirname(os.path.realpath(__file__)), "reply_templates.json"
        )
        with open(path, "r") as file:
            self.reply_templates = json.load(file)
        reply_templates = ReplyTemplates.Schema().load(self.reply_templates)
        self.reply_templates = reply_templates
        self.router = BotRouter(self)
        self.router.create_command_route(Command.START, start_handler)
        self.router.create_command_route(Command.STOP, stop_handler)
        self.router.create_command_route(Command.SHORT_START, start_handler)
        self.router.create_command_route(Command.SHORT_STOP, stop_handler)
        self.router.create_command_route(
            Command.GET_BALANCES, get_balances_handler
        )
        self.router.create_command_route(
            Command.SHORT_GET_BALANCES, get_balances_handler
        )
        self.router.create_command_route(
            Command.GET_PREV_SESSION, get_prev_session_handler
        )
        self.router.create_command_route(
            Command.SHORT_GET_PREV_SESSION, get_prev_session_handler
        )
        self.router.create_command_route(Command.GET_RULES, get_rules_handler)
        self.router.create_command_route(
            Command.SHORT_GET_RULES, get_rules_handler
        )
        self.router.create_query_route(Query.NUM_PLAYERS, players_num_handler)
        self.router.create_query_route(Query.MAKE_A_BET, bet_handler)
        self.router.create_query_route(Query.GET_CARD, get_card_handler)
        self.router.create_query_route(Query.ENOUGH, enough_handler)

    async def connect(self, app: "Application") -> None:
        self.http_session = aiohttp.ClientSession()
        self.start()

    async def send_message(
        self,
        chat_id: int,
        text: str,
        markup: dict | None = None,
    ) -> SendMessageResponse | None:
        await asyncio.sleep(0.1)
        url, payload = self.app.store.tg_api.get_url("sendMessage"), None
        if markup:
            payload = {
                "chat_id": chat_id,
                "text": text,
                "reply_markup": markup,
                "cache_time": 2,
            }
        else:
            payload = {
                "chat_id": chat_id,
                "text": text,
                "reply_markup": {"inline_keyboard": [[]]},
            }
        async with self.http_session.post(url, json=payload) as resp:
            res_dict = await resp.json()
            return SendMessageResponse.Schema().load(res_dict)

    @property
    def blackjack(self):
        return self.app.store.blackjack

    @property
    def tg_api(self):
        return self.app.store.tg_api

    async def send_reply(
        self, reply_name: ReplyTemplates, chat_id: int
    ) -> None:
        reply_template = next(
            reply
            for reply in self.reply_templates.data
            if reply.name == reply_name
        )
        if reply_template is None:
            raise ReplyTemplateNotFoundError(reply_template)
        await self.send_message(
            chat_id=chat_id,
            text=reply_template.content.text,
            markup=Markup.Schema().dump(
                reply_template.content.markup,
            ),
        )

    async def _worker(self):
        while True:
            async with self.app.database.session() as db_session:
                update = await self.tg_api.queue.get()
                await self.router.navigate(update, db_session)

    def start(self):
        self.tg_api.logger.info("start working")
        self.worker_tasks = [
            asyncio.create_task(self._worker())
            for _ in range(self.app.config.bot.num_workers)
        ]

    async def disconnect(self, app: "Application") -> None:
        await self.queue.join()
        for worker_task in self.worker_tasks:
            worker_task.cancel()
