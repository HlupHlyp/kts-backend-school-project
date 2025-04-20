import typing
from collections.abc import Callable

from app.store.bot.dataclasses import Route
from app.store.tg_api.dataclasses import UpdateObj

COMMANDS: set[str] = {"start@SC17854_bot", "stop@SC17854_bot"}

if typing.TYPE_CHECKING:
    from app.store.bot.manager import BotManager


class BotRouter:
    def __init__(self, manager: "BotManager"):
        self.routes: list[Route] = []
        self.manager = manager

    def create_route(
        self,
        route_str: str,
        func: Callable[["BotManager", UpdateObj, list | None], None],
    ) -> None:
        self.routes.append(
            Route(
                route_str=route_str,
                action=func,
            )
        )

    async def navigate(self, update: UpdateObj) -> None:
        # Бот реагирует только на команды и нажатия на кнопки.
        # Routes делятся на посвященные коммандам и кнопкам.
        # Команды начинаюся с /, а вызовы кнопок идут без префикса.
        # Данная функция смотрит пришло сообщение или callback_query.
        # Если пришло сообщение, то смотрит начинается ли оно с / и,
        # ищет route для него.
        # Если пришел callback, то просто ищет route.
        # Также здесь выделяются параметры
        if update.message is not None:
            if str(update.message.text).startswith("/"):
                command = str(update.message.text).split("/")[1]
                if command in COMMANDS:
                    route = next(
                        route
                        for route in self.routes
                        if route.route_str == command
                    )
                    if route is not None:
                        await route.action(
                            update=update,
                            manager=self.manager,
                        )
                    else:
                        self.manager.logger.error(
                            "Command's route hasn't been found"
                        )
                        raise Exception
        elif update.callback_query is not None:
            query = str(update.callback_query.data).split("/")[0]
            route = next(
                route for route in self.routes if route.route_str == query
            )
            if route is not None:
                await route.action(update=update, manager=self.manager)
