# from dataclasses import dataclass, field

from sqlalchemy import (
    BigInteger,
    CheckConstraint,
    Column,
    # DateTime,
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
        cascade="all, delete-orphan",
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
        cascade="all, delete-orphan",
    )
    hands: Mapped[list["HandModel"]] = relationship(
        "HandModel",
        back_populates="player",
        cascade="all, delete-orphan",
    )


class HandModel(BaseModel):
    __tablename__ = "hands"
    id = Column(BigInteger, primary_key=True)
    player_id: Mapped[int] = mapped_column(
        ForeignKey("players.id", ondelete="CASCADE")
    )
    rate = Column(BigInteger, nullable=False)
    player: Mapped[list["PlayerModel"]] = relationship(
        "PlayerModel",
        back_populates="hands",
        cascade="all, delete-orphan",
    )
    cards: Mapped[list["CardModel"]] = relationship(
        "CardModel",
        back_populates="hand",
        cascade="all, delete-orphan",
    )


class CardModel(BaseModel):
    __tablename__ = "cards"
    id = Column(BigInteger, primary_key=True)
    score = Column(BigInteger, nullable=False, unique=True)
    name = Column(
        String(100),
        CheckConstraint(
            "name IN ('Валет','Дама','Король','Туз') ",
            name="check_card_name",
        ),
        nullable=True,
    )
    suit = Column(
        String(100),
        CheckConstraint(
            "suit IN ('♥','♦','♣','♠')",
            name="check_card_suit",
        ),
        nullable=False,
    )
    hand_id: Mapped[int] = mapped_column(
        ForeignKey("hands.id", ondelete="CASCADE"), nullable=True
    )
    player: Mapped[list["HandModel"]] = relationship(
        "HandModel",
        back_populates="cards",
        cascade="all, delete-orphan",
    )
