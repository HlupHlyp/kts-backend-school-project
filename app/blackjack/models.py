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
    id: Mapped[int] = mapped_column(primary_key=True)
    chat_id: Mapped[int] = mapped_column(BigInteger, index=True, unique=True)
    status: Mapped[str] = mapped_column(
        String,
        CheckConstraint(
            "status IN ('sleeping','waiting_for_num','waiting_for_users',"
            "'polling')",
            name="check_game_session_status",
        ),
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
    right_hand: Mapped[dict | None] = mapped_column(JSON)
    balance: Mapped[int] = mapped_column()
    bet: Mapped[int | None] = mapped_column()

    game_session: Mapped[list["GameSessionModel"]] = relationship(
        "GameSessionModel",
        back_populates="players",
    )

    __table_args__ = (
        UniqueConstraint("game_session_id", "tg_id", name="session_tg_unique"),
    )
