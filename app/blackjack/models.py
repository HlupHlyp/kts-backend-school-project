import enum

from sqlalchemy import (
    BigInteger,
    Enum,
    ForeignKey,
    UniqueConstraint,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.store.database.sqlalchemy_base import BaseModel


class GameSessionStatus(enum.Enum):
    sleeping = 0
    waiting_for_num = 1
    waiting_for_users = 2
    polling = 3


class ParticipantStatus(enum.Enum):
    sleeping = 0
    active = 1
    polling = 2
    assembled = 3


class GameSessionModel(BaseModel):
    __tablename__ = "game_sessions"
    id: Mapped[int] = mapped_column(primary_key=True)
    chat_id: Mapped[int] = mapped_column(BigInteger, index=True, unique=True)
    status: Mapped[GameSessionStatus] = mapped_column(
        Enum(
            GameSessionStatus,
            create_constraint=True,
            native_enum=False,
            validate_strings=True,
        )
    )
    num_users: Mapped[int | None] = mapped_column()

    participants: Mapped[list["ParticipantModel"]] = relationship(
        "ParticipantModel",
        back_populates="game_session",
    )
    dealer_cards: Mapped[dict | None] = mapped_column(JSONB)


class ParticipantModel(BaseModel):
    __tablename__ = "participants"
    id: Mapped[int] = mapped_column(primary_key=True)
    game_session_id: Mapped[int] = mapped_column(
        ForeignKey("game_sessions.id", ondelete="CASCADE"), index=True
    )
    player_id: Mapped[int] = mapped_column(
        ForeignKey("players.id", ondelete="CASCADE"), index=True
    )
    status: Mapped[str] = mapped_column(
        Enum(
            ParticipantStatus,
            create_constraint=True,
            native_enum=False,
            validate_strings=True,
        )
    )
    right_hand: Mapped[dict | None] = mapped_column(JSONB)
    bet: Mapped[int | None] = mapped_column()

    game_session: Mapped["GameSessionModel"] = relationship(
        "GameSessionModel",
        back_populates="participants",
    )

    player: Mapped["PlayerModel"] = relationship(
        "PlayerModel",
        back_populates="participants",
    )

    __table_args__ = (
        UniqueConstraint(
            "game_session_id", "player_id", name="session_tg_unique"
        ),
    )


class PlayerModel(BaseModel):
    __tablename__ = "players"
    id: Mapped[int] = mapped_column(primary_key=True)
    balance: Mapped[int] = mapped_column()
    tg_id: Mapped[int] = mapped_column(BigInteger, index=True, unique=True)
    username: Mapped[str] = mapped_column(unique=True)

    participants: Mapped[list["ParticipantModel"]] = relationship(
        "ParticipantModel",
        back_populates="player",
    )
