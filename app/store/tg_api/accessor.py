import typing

from app.base.base_accessor import BaseAccessor
from app.clients.tg import TgClient
from app.store.tg_api.poller import Poller

if typing.TYPE_CHECKING:
    from app.web.app import Application


class TgApiAccessor(BaseAccessor):
    def __init__(self, app: "Application", token: str, *args, **kwargs):
        super().__init__(app, *args, **kwargs)
        self.tg_client = TgClient(token)
        self.poller: Poller | None = None
        self.offset: int | None = None

    async def connect(self, app: "Application") -> None:
        self.offset = 0
        self.poller = Poller(app.store)
        self.logger.info("start polling")
        self.poller.start()

    async def disconnect(self, app: "Application") -> None:
        if self.poller:
            await self.poller.stop()

    async def poll(self):
        updates = await self.tg_client.get_updates(
            offset=self.offset, timeout=25
        )
        updates = await self.tg_client.get_updates_in_objects(
            offset=self.offset, timeout=25
        )
        for update in updates.result:
            self.offset = update.update_id + 1
        await self.app.store.bots_manager.handle_updates(updates)
