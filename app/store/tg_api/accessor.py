import asyncio
import typing

import aiohttp

from app.base.base_accessor import BaseAccessor
from app.store.tg_api.dataclasses import GetUpdatesResponse
from app.store.tg_api.poller import Poller

if typing.TYPE_CHECKING:
    from app.web.app import Application

TG_BOT_ADDR = "https://api.telegram.org/bot"
TIMEOUT = 25


class TgApiAccessor(BaseAccessor):
    def __init__(self, app: "Application", *args, **kwargs):
        super().__init__(app, *args, **kwargs)
        self.poller: Poller | None = None
        self.offset: int | None = None
        self.base_url = f"{TG_BOT_ADDR}{self.app.config.bot.token}/"

    def get_url(self, method: str) -> str:
        return f"{self.base_url}{method}"

    async def get_updates_in_objects(
        self,
        session: aiohttp.ClientSession,
        offset: int | None = None,
        timeout: int = TIMEOUT,
    ) -> GetUpdatesResponse | None:
        url = self.get_url("getUpdates")
        params, res_dict = {}, {}
        if offset:
            params["offset"] = offset
        if timeout:
            params["timeout"] = timeout
        async with session.get(url, params=params) as resp:
            res_dict = await resp.json()
            print(f"Результаты приема: {res_dict}")
        return GetUpdatesResponse.Schema().load(res_dict, partial=True)

    async def connect(self, app: "Application") -> None:
        self.queue = asyncio.Queue()
        self.http_session = aiohttp.ClientSession()
        self.poller = Poller(app.store)
        self.offset = 0
        self.poller.start()

    async def disconnect(self, app: "Application") -> None:
        if self.poller:
            await self.poller.stop()

    async def poll(self) -> None:
        updates = await self.get_updates_in_objects(
            session=self.http_session,
            offset=self.offset,
            timeout=TIMEOUT,
        )
        if updates is not None:
            for update in updates.result:
                self.offset = update.update_id + 1
                self.queue.put_nowait(update)
