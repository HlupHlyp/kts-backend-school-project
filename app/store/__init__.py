# from .store import Store

# __all__ = ("Store",)
import typing

from app.store.database.database import Database

if typing.TYPE_CHECKING:
    from app.web.app import Application


class Store:
    def __init__(self, app: "Application"):
        # from app.store.admin.accessor import AdminAccessor
        from app.store.bot.manager import BotManager
        from app.store.tg_api.accessor import TgApiAccessor

        # self.quizzes = QuizAccessor(app)
        # self.admins = AdminAccessor(app)
        self.Tg_api = TgApiAccessor(app, token=app.config.bot.token)
        self.bots_manager = BotManager(app)


def setup_store(app: "Application"):
    app.database = Database(app)
    app.on_startup.append(app.database.connect)
    app.on_cleanup.append(app.database.disconnect)
    app.store = Store(app)
