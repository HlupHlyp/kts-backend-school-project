import typing

import aiohttp

from app.base.base_accessor import BaseAccessor
from app.store.tg_api.dataclasses import GetUpdatesResponse
from app.store.tg_api.poller import Poller

if typing.TYPE_CHECKING:
    from app.web.app import Application


class TgApiAccessor(BaseAccessor):
    def __init__(self, app: "Application", token: str, *args, **kwargs):
        super().__init__(app, *args, **kwargs)
        self.poller: Poller | None = None
        self.offset: int | None = None
        self.base_url = f"https://api.telegram.org/bot{token}/"

    def get_url(self, method: str) -> str:
        return f"{self.base_url}{method}"

    async def get_updates_in_objects(
        self, offset: int | None = None, timeout: int = 0
    ) -> GetUpdatesResponse:
        url = self.get_url("getUpdates")
        params, res_dict = {}, {}
        if offset:
            params["offset"] = offset
        if timeout:
            params["timeout"] = timeout
        async with aiohttp.ClientSession() as session:
            async with session.get(url, params=params) as resp:
                res_dict = await resp.json()
        return GetUpdatesResponse.Schema().load(res_dict)

    async def connect(self, app: "Application") -> None:
        self.offset = 0
        self.poller = Poller(app.store)
        self.logger.info("start polling")
        self.poller.start()

    async def disconnect(self, app: "Application") -> None:
        if self.poller:
            await self.poller.stop()

    async def poll(self) -> None:
        updates = await self.get_updates_in_objects(
            offset=self.offset, timeout=25
        )
        for update in updates.result:
            self.offset = update.update_id + 1
        await self.app.store.bots_manager.handle_updates(updates)
