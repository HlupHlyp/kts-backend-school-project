import enum
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


class CardSuit(enum.Enum):
    hearts = 0
    crosses = 1
    spades = 2
    diamonds = 3


@dataclass
class CardName(enum.Enum):
    one = 1
    two = 2
    three = 3
    four = 4
    five = 5
    six = 6
    seven = 7
    eight = 8
    nine = 9
    ten = 10
    king = 11
    queen = 12
    jack = 13
    ace = 14


@dataclass
class Card(Base):
    suit: CardSuit
    name: CardName
    weight: int


@dataclass
class Cards(Base):
    cards: list[Card] | None = None
