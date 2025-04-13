from app.store.tg_api.dataclasses import UpdateObj
import typing

if typing.TYPE_CHECKING:
    from app.web.app import Application
    from app.store.bot.manager import BotManager


class BotRouter:
    def __init__(self, manager: "BotManager"):
        self.routes = {}
        self.manager = manager

    def create_route(self, trigger: str, action, is_command: bool = False):
        self.routes[trigger] = {"action": action, "is_command": is_command}

    async def navigate(self, update: UpdateObj):
        if update.message is not None:
            if str(update.message.text).startswith("/"):
                command = str(update.message.text).split("/")
                if (
                    command[1] in self.routes
                    and self.routes[command[1]]["is_command"]
                ):
                    params = []
                    for i in range(2, len(command)):
                        params += command[i]
                    await self.routes[command[1]]["action"](
                        update=update, params=params, manager=self.manager
                    )
        elif update.callback_query is not None:
            query = str(update.callback_query.data).split("/")
            if (
                query[0] in self.routes
                and not self.routes[query[0]]["is_command"]
            ):
                params = []
                for i in range(1, len(query)):
                    params += query[i]
                await self.routes[query[0]]["action"](
                    update=update, manager=self.manager, params=params
                )
