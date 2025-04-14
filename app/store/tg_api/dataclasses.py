from dataclasses import field
from typing import ClassVar

from marshmallow import Schema
from marshmallow_dataclass import dataclass


@dataclass
class AcceptedGiftTypes:
    unlimited_gifts: bool
    limited_gifts: bool
    unique_gifts: bool
    premium_subscription: bool


@dataclass
class Chat:
    id: int
    type: str
    all_members_are_administrators: bool
    accepted_gift_types: AcceptedGiftTypes
    first_name: str | None = None
    last_name: str | None = None
    username: str | None = None
    title: str | None = None


@dataclass
class MessageFrom:
    id: int
    first_name: str
    is_bot: bool
    language_code: str | None = None
    last_name: str | None = None
    username: str | None = None
    chat: Chat | None = None


@dataclass
class Entity:
    offset: int | None = None
    length: int | None = None
    type: str | None = None


@dataclass
class Button:
    text: str
    callback_data: str


@dataclass
class ReplyMarkup:
    inline_keyboard: list[list[Button]]


@dataclass
class Message:
    message_id: int
    from_: MessageFrom = field(metadata={"data_key": "from"})
    chat: Chat
    date: int
    entities: list[Entity] | None
    text: str | None = None
    data: str | None = None
    reply_markup: ReplyMarkup | None = None


@dataclass
class CallbackQuery:
    id: int
    from_: MessageFrom = field(metadata={"data_key": "from"})
    chat_instance: int
    message: Message | None = None
    data: str | None = None


@dataclass
class UpdateObj:
    update_id: int
    message: Message | None = None
    edited_message: Message | None = None
    callback_query: CallbackQuery | None = None


@dataclass
class GetUpdatesResponse:
    ok: bool
    result: list[UpdateObj]

    Schema: ClassVar[type[Schema]] = Schema


@dataclass
class SendMessageResponse:
    ok: bool
    result: Message

    Schema: ClassVar[type[Schema]] = Schema
