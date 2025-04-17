from sqlalchemy import (
    BigInteger,
    CheckConstraint,
    ForeignKey,
    String,
    UniqueConstraint,
    Enum,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.store.database.sqlalchemy_base import BaseModel
import enum


class GameSessionStatus(enum.Enum):
    sleeping = 0
    waiting_for_num = 1
    waiting_for_users = 2
    polling = 3


class PlayerStatus(enum.Enum):
    sleeping = 0
    active = 1
    polling = 2
    assembled = 3
    dealer = 4


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

    players: Mapped[list["PlayerModel"]] = relationship(
        "PlayerModel",
        back_populates="game_session",
    )


class PlayerModel(BaseModel):
    __tablename__ = "players"
    id: Mapped[int] = mapped_column(primary_key=True)
    game_session_id: Mapped[int] = mapped_column(
        ForeignKey("game_sessions.id", ondelete="CASCADE"), index=True
    )
    status: Mapped[str] = mapped_column(
        String,
        CheckConstraint(
            "status IN ('sleeping','active','polling', 'assembled', 'dealer') ",
            name="check_user2session_status",
        ),
    )
    tg_id: Mapped[int] = mapped_column(BigInteger, index=True)
    right_hand: Mapped[dict | None] = mapped_column(JSONB)
    balance: Mapped[int] = mapped_column()
    bet: Mapped[int | None] = mapped_column()

    game_session: Mapped[list["GameSessionModel"]] = relationship(
        "GameSessionModel",
        back_populates="players",
    )

    __table_args__ = (
        UniqueConstraint("game_session_id", "tg_id", name="session_tg_unique"),
    )
