import typing

from app.store.database.database import Database

if typing.TYPE_CHECKING:
    from app.web.app import Application


class Store:
    def __init__(self, app: "Application"):
        from app.store.blackjack.accessor import BlackjackAccessor
        from app.store.bot.manager import BotManager
        from app.store.tg_api.accessor import TgApiAccessor

        self.tg_api = TgApiAccessor(app)
        self.bots_manager = BotManager(app)
        self.blackjack = BlackjackAccessor(app)


def setup_store(app: "Application"):
    app.database = Database(app)
    app.on_startup.append(app.database.connect)
    app.on_cleanup.append(app.database.disconnect)
    app.store = Store(app)
