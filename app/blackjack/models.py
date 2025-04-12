from sqlalchemy import (
    JSON,
    BigInteger,
    CheckConstraint,
    Column,
    ForeignKey,
    String,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.store.database.sqlalchemy_base import BaseModel


class GameSessionModel(BaseModel):
    __tablename__ = "game_sessions"
    id = Column(BigInteger, primary_key=True)
    chat_id = Column(BigInteger, nullable=False, index=True, unique=True)
    status = Column(
        String(100),
        CheckConstraint(
            "status IN ('sleeping','waiting_for_num','waiting_for_users',"
            "'polling')",
            name="check_game_session_status",
        ),
        nullable=False,
    )
    num_users = Column(BigInteger, nullable=True)
    players: Mapped[list["PlayerModel"]] = relationship(
        "PlayerModel",
        back_populates="game_session",
    )


class PlayerModel(BaseModel):
    __tablename__ = "players"
    id = Column(BigInteger, primary_key=True)
    game_session_id: Mapped[int] = mapped_column(
        ForeignKey("game_sessions.id", ondelete="CASCADE")
    )
    status = Column(
        String(100),
        CheckConstraint(
            "status IN ('sleeping','active','polling', 'assembled', 'dealer') ",
            name="check_user2session_status",
        ),
        nullable=False,
    )
    tg_id = Column(BigInteger, nullable=False, index=True, unique=True)
    score = Column(BigInteger, nullable=False)
    game_session: Mapped[list["GameSessionModel"]] = relationship(
        "GameSessionModel",
        back_populates="players",
    )
    right_hand = Column(JSON, nullable=True)
