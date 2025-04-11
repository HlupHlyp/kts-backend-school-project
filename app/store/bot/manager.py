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

    async def handle_updates(self, updates: list[UpdateObj]):
        for update in updates.result:
            if update.message is not None:
                await self.app.store.Tg_api.tg_client.send_message(
                    chat_id=update.message.chat.id, text="Hello world!"
                )
            elif update.edited_message is not None:
                await self.app.store.Tg_api.tg_client.send_message(
                    chat_id=update.edited_message.chat.id, text="Hello world!"
                )
            else:
                await self.app.store.Tg_api.tg_client.send_message(
                    chat_id=update.callback_query.message.chat.id,
                    text="Hello world!",
                )
