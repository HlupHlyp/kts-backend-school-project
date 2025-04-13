from sqlalchemy import (
    JSON,
    BigInteger,
    CheckConstraint,
    ForeignKey,
    String,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.store.database.sqlalchemy_base import BaseModel


class GameSessionModel(BaseModel):
    __tablename__ = "game_sessions"
    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    chat_id: Mapped[int] = mapped_column(
        BigInteger, nullable=False, index=True, unique=True
    )
    status: Mapped[str] = mapped_column(
        String(100),
        CheckConstraint(
            "status IN ('sleeping','waiting_for_num','waiting_for_users',"
            "'polling')",
            name="check_game_session_status",
        ),
        nullable=False,
    )
    num_users: Mapped[int] = mapped_column(BigInteger, nullable=True)
    players: Mapped[list["PlayerModel"]] = relationship(
        "PlayerModel",
        back_populates="game_session",
    )


class PlayerModel(BaseModel):
    __tablename__ = "players"
    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    game_session_id: Mapped[int] = mapped_column(
        ForeignKey("game_sessions.id", ondelete="CASCADE")
    )
    status: Mapped[str] = mapped_column(
        String(100),
        CheckConstraint(
            "status IN ('sleeping','active','polling', 'assembled', 'dealer') ",
            name="check_user2session_status",
        ),
        nullable=False,
    )
    tg_id: Mapped[int] = mapped_column(
        BigInteger, nullable=False, index=True, unique=True
    )
    game_session: Mapped[list["GameSessionModel"]] = relationship(
        "GameSessionModel",
        back_populates="players",
    )
    right_hand: Mapped[dict] = mapped_column(JSON, nullable=True)
    balance: Mapped[int] = mapped_column(BigInteger, nullable=False)
    bet: Mapped[int] = mapped_column(BigInteger, nullable=True)
    __table_args__ = (
        UniqueConstraint("game_session_id", "tg_id", name="session_tg_unique"),
    )
