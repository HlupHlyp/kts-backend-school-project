import enum
import typing
from collections.abc import Callable
from dataclasses import field

from marshmallow_dataclass import dataclass

if typing.TYPE_CHECKING:
    from app.store.bot.manager import BotManager
    from app.store.tg_api.dataclasses import UpdateObj

from app.store.tg_api.dataclasses import Base

C = typing.TypeVar("C", bound="Cards")


@dataclass
class Route:
    route_str: str
    action: Callable[["BotManager", "UpdateObj", list | None], None]


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


class CardSuit(enum.StrEnum):
    HEARTS = "♥"
    CROSSES = "♣"
    SPADES = "♠"
    DIAMONDS = "♦"


class CardName(enum.StrEnum):
    ONE = "1"
    TWO = "2"
    THREE = "3"
    FOUR = "4"
    FIVE = "5"
    SIX = "6"
    SEVEN = "7"
    EIGHT = "8"
    NINE = "9"
    TEN = "10"
    KING = "Король"
    QUEEN = "Королева"
    JACK = "Валет"
    ACE = "Туз"


@dataclass
class Card(Base):
    suit: CardSuit
    name: CardName
    weight: int


@dataclass
class Cards(Base):
    cards: list[Card] = field(default_factory=list)

    def to_dict(self) -> dict:
        return Cards.Schema().dump(self.cards)

    def from_dict(self, cards: dict) -> C:
        return Cards.Schema().load(cards)
