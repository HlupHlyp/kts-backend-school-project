import typing
from collections.abc import Callable

from marshmallow_dataclass import dataclass

if typing.TYPE_CHECKING:
    from app.store.bot.manager import BotManager
    from app.store.tg_api.dataclasses import UpdateObj

from app.store.tg_api.dataclasses import Base


@dataclass
class Action:
    func: Callable[["BotManager", "UpdateObj", list | None], None]
    is_command: bool = False


@dataclass
class Route:
    trigger: str
    action: Action


@dataclass
class Button:
    text: str | None = None
    callback_data: str | None = None


@dataclass
class Markup(Base):
    inline_keyboard: list[list[Button]] | None = None


@dataclass
class Content:
    text: str
    markup: Markup


@dataclass
class Reply:
    content: Content
    name: str | None = None


@dataclass
class ReplyTemplates(Base):
    data: list[Reply]
