import enum

from sqlalchemy import (
    BigInteger,
    Enum,
    ForeignKey,
    UniqueConstraint,
    CheckConstraint,
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
    is_stopped: Mapped[bool] = mapped_column(default=False)


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

    @property
    def is_polling(self):
        return self.status == ParticipantStatus.POLLING


class PlayerModel(BaseModel):
    __tablename__ = "players"
    id: Mapped[int] = mapped_column(primary_key=True)
    balance: Mapped[int] = mapped_column()
    tg_id: Mapped[int] = mapped_column(BigInteger, index=True, unique=True)
    username: Mapped[str | None] = mapped_column(unique=True, nullable=True)
    firstname: Mapped[str | None] = mapped_column(nullable=True)

    participants: Mapped[list["ParticipantModel"]] = relationship(
        "ParticipantModel",
        back_populates="player",
    )

    @property
    def name(self):
        return self.username if self.username is not None else self.firstname

    table_args = (
        CheckConstraint(
            "firstname is not null or username is not null  or bet < 0",
            name="first_name or username",
        ),
    )


class AdminModel(BaseModel):
    """Пока поместил модельку админа сюда, поскольку в app.admin.models alembic
    ее игнорирует
    """

    __tablename__ = "admins"
    id: Mapped[int] = mapped_column(primary_key=True)
    email: Mapped[str] = mapped_column(unique=True)
    password: Mapped[str] = mapped_column()
