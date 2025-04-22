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
    all_members_are_administrators: bool | None = None
    accepted_gift_types: AcceptedGiftTypes | None = None
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
class File:
    file_id: str
    file_unique_id: str
    file_size: int


@dataclass
class Document(File):
    file_name: str
    mime_type: str


@dataclass
class Photo(File):
    width: int
    height: int


@dataclass
class Voice(File):
    duration: int
    mime_type: str


@dataclass
class Thumbnail(File):
    width: int
    height: int


@dataclass
class VideoNote(File):
    duration: int
    thumbnail: Thumbnail
    thumb: Thumbnail
    length: int


@dataclass
class Sticker(File):
    width: int
    height: int
    emoji: str
    set_name: str
    is_animated: bool
    is_video: bool
    type: str
    thumbnail: Thumbnail
    thumb: Thumbnail


@dataclass
class Animation(Document, Photo):
    duration: int


@dataclass
class Video(VideoNote, Photo):
    mime_type: str | None = None
    file_name: str | None = None
    length: int | None = None


@dataclass
class NewParticipant:
    id: int
    is_bot: bool
    first_name: str
    username: str
    last_name: str | None = None
    language_code: str | None = None


@dataclass
class Reply2Message:
    message_id: int
    from_: MessageFrom = field(metadata={"data_key": "from"})
    chat: Chat
    date: int
    text: str | None = None


@dataclass
class Message:
    message_id: int
    from_: MessageFrom = field(metadata={"data_key": "from"})
    chat: Chat
    date: int
    entities: list[Entity] | None = None
    text: str | None = None
    data: str | None = None
    reply_markup: ReplyMarkup | None = None
    document: Document | None = None
    photo: list[Photo] | None = None
    voice: Voice | None = None
    video_note: VideoNote | None = None
    sticker: Sticker | None = None
    animation: Animation | None = None
    video: Video | None = None
    new_chat_participant: NewParticipant | None = None
    new_chat_member: NewParticipant | None = None
    new_chat_members: list[NewParticipant] | None = None
    left_chat_participant: NewParticipant | None = None
    left_chat_member: NewParticipant | None = None
    edit_date: int | None = None
    reply_to_message: Reply2Message | None = None


@dataclass
class User:
    id: int
    is_bot: bool
    first_name: str
    username: str


@dataclass
class ChatMember:
    user: User
    status: str


@dataclass
class MyChatMember:
    chat: Chat
    from_: MessageFrom = field(metadata={"data_key": "from"})
    date: int
    new_chat_member: ChatMember
    old_chat_member: ChatMember


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
    my_chat_member: MyChatMember | None = None

    @property
    def chat_id(self) -> int:
        if self.message is not None:
            return self.message.chat.id
        if self.callback_query is not None:
            return self.callback_query.message.chat.id
        return None

    @property
    def tg_id(self) -> int:
        if self.message is not None:
            return self.message.from_.id
        if self.callback_query is not None:
            return self.callback_query.from_.id
        return None

    @property
    def username(self) -> str:
        if self.message is not None:
            return self.message.from_.username
        if self.callback_query is not None:
            return self.callback_query.from_.username
        return None

    @property
    def first_name(self) -> str:
        if self.message is not None:
            return self.message.from_.first_name
        if self.callback_query is not None:
            return self.callback_query.from_.first_name
        return None


@dataclass
class Base:
    Schema: ClassVar[type[Schema]] = Schema


@dataclass
class GetUpdatesResponse(Base):
    ok: bool
    result: list[UpdateObj]


@dataclass
class SendMessageResponse(Base):
    ok: bool
    result: Message | None = None
    error_code: int | None = None
    description: str | None = None
