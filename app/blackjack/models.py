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


class GameSessionStatus(enum.StrEnum):
    SLEEPING = "SLEEPING"
    WAITING_FOR_NUM = "WAITING_FOR_NUM"
    WAITING_FOR_USERS = "WAITING_FOR_USERS"
    POLLING = "POLLING"


class ParticipantStatus(enum.StrEnum):
    SLEEPING = "SLEEPING"
    ACTIVE = "ACTIVE"
    POLLING = "POLLING"
    ASSEMBLED = "ASSEMBLED"


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
    dealer_cards: Mapped[dict] = mapped_column(JSONB, default={})


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
    right_hand: Mapped[dict] = mapped_column(JSONB, default={})
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
