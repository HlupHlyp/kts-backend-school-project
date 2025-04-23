from sqlalchemy.orm import Mapped, mapped_column

from app.store.database.sqlalchemy_base import BaseModel


class AdminModel(BaseModel):
    __tablename__ = "admins"
    id: Mapped[int] = mapped_column(primary_key=True)
    email: Mapped[str] = mapped_column(unique=True)
    password: Mapped[str] = mapped_column()
