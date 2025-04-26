import enum
import typing

from sqlalchemy.ext.asyncio import AsyncSession

from app.store.bot.exceptions import (
    CommandRouteNotFoundError,
    QueryRouteNotFoundError,
)
from app.store.tg_api.dataclasses import UpdateObj

if typing.TYPE_CHECKING:
    from app.store.bot.manager import BotManager
    from app.store.tg_api.dataclasses import UpdateObj


class Query(enum.StrEnum):
    NUM_PLAYERS = "num_players"
    MAKE_A_BET = "make_a_bet"
    GET_CARD = "get_card"
    ENOUGH = "enough"


class Command(enum.StrEnum):
    START = "start@SC17854_bot"
    STOP = "stop@SC17854_bot"
    SHORT_START = "start"
    SHORT_STOP = "stop"
    GET_BALANCES = "get_balances@SC17854_bot"
    SHORT_GET_BALANCES = "get_balances"
    GET_PREV_SESSION = "get_prev_session@SC17854_bot"
    SHORT_GET_PREV_SESSION = "get_prev_session"
    GET_RULES = "get_rules@SC17854_bot"
    SHORT_GET_RULES = "get_rules"


class Handler(typing.Protocol):
    def __call__(
        self, manager: "BotManager", update: "UpdateObj", session: AsyncSession
    ) -> None: ...


class BotRouter:
    def __init__(self, manager: "BotManager"):
        self.query_routes: dict[Query, Handler] = {}
        self.command_routes: dict[Command, Handler] = {}
        self.manager = manager

    def create_command_route(
        self,
        command: Command,
        func: Handler,
    ) -> None:
        self.command_routes[command] = func

    def create_query_route(
        self,
        query: Query,
        func: Handler,
    ) -> None:
        self.query_routes[query] = func

    async def navigate(self, update: UpdateObj, session: AsyncSession) -> None:
        # Бот реагирует только на команды и нажатия на кнопки.
        # Routes делятся на посвященные коммандам и кнопкам.
        # Команды начинаюся с /, а вызовы кнопок идут без префикса.
        # Данная функция смотрит пришло сообщение или callback_query.
        # Если пришло сообщение, то смотрит начинается ли оно с / и,
        # ищет route для него.
        # Если пришел callback, то просто ищет route.
        # Также здесь выделяются параметры
        log = f"Объект в навигаторе: {update}"
        self.manager.logger.info(log)
        if update.message is not None:
            if str(update.message.text).startswith("/"):
                command = str(update.message.text).split("/")[1]
                self.manager.logger.info("Объект в навигаторе: %s", update)
                if command in [item.value for item in Command]:
                    try:
                        handler = self.command_routes[command]
                    except KeyError as e:
                        raise CommandRouteNotFoundError(command) from e
                    else:
                        log = f"Хэндлер: {handler}"
                        self.manager.logger.info(log)
                        await handler(self.manager, update, session)
        elif update.callback_query is not None:
            query = str(update.callback_query.data).split("/")[0]
            try:
                handler = self.query_routes[query]
            except KeyError as e:
                raise QueryRouteNotFoundError(query) from e
            else:
                await handler(self.manager, update, session)
