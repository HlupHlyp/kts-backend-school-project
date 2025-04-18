import typing
from collections.abc import Callable

from app.store.bot.dataclasses import Action, Route
from app.store.tg_api.dataclasses import UpdateObj

if typing.TYPE_CHECKING:
    from app.store.bot.manager import BotManager


class BotRouter:
    def __init__(self, manager: "BotManager"):
        self.routes: list[Route] = []
        self.manager = manager

    def create_route(
        self,
        trigger: str,
        func: Callable[["BotManager", UpdateObj, list | None], None],
        is_command: bool = False,
    ) -> None:
        self.routes.append(
            Route(
                trigger=trigger,
                action=Action(func=func, is_command=is_command),
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
                command = str(update.message.text).split("/")
                route = next(
                    filter(
                        lambda route: route.trigger == command[1], self.routes
                    )
                )
                if route is not None and route.action.is_command:
                    params = []
                    for i in range(2, len(command)):
                        params += command[i]
                    await route.action.func(
                        update=update, params=params, manager=self.manager
                    )
        elif update.callback_query is not None:
            query = str(update.callback_query.data).split("/")
            route = next(
                filter(lambda route: route.trigger == query[0], self.routes)
            )

            if route is not None and not route.action.is_command:
                params = query[1:]
                await route.action.func(
                    update=update, manager=self.manager, params=params
                )
