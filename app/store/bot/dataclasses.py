import enum
from dataclasses import field

from marshmallow_dataclass import dataclass

from app.store.tg_api.dataclasses import Base


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

    def __str__(self):
        return f"{self.name.value}{self.suit.value}"


@dataclass
class Cards(Base):
    cards: list[Card] = field(default_factory=list)

    def to_dict(self) -> dict:
        return Cards.Schema().dump(self)

    def from_dict(self, cards: dict) -> "Cards":
        return Cards.Schema().load(cards)

    def __str__(self):
        message = ""
        for card in self.cards:
            message += f"{card.name.value}{card.suit.value}"
            message += "  "
        return message

    def add_card(self, card: Card) -> None:
        self.cards.append(card)
