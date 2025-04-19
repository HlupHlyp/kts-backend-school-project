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
        timeout: int = 0,
    ) -> GetUpdatesResponse | None:
        url = self.get_url("getUpdates")
        params, res_dict = {}, {}
        if offset:
            params["offset"] = offset
        if timeout:
            params["timeout"] = timeout
        async with session.get(url, params=params) as resp:
            res_dict = await resp.json()
        return GetUpdatesResponse.Schema().load(res_dict, partial=True)

    async def connect(self, app: "Application") -> None:
        self.offset = 0
        self.poller = Poller(app.store)
        self.logger.info("start polling")
        self.poller.start()

    async def disconnect(self, app: "Application") -> None:
        if self.poller:
            await self.poller.stop()

    async def poll(self) -> None:
        async with aiohttp.ClientSession() as session:
            updates = await self.get_updates_in_objects(
                session=session, offset=self.offset, timeout=TIMEOUT
            )
            if updates is not None:
                for update in updates.result:
                    self.offset = update.update_id + 1
                await self.app.store.bots_manager.handle_updates(
                    session=session, updates=updates
                )
