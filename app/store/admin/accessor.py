import hashlib
from typing import TYPE_CHECKING

from sqlalchemy import select

from app.base.base_accessor import BaseAccessor
from app.blackjack.models import AdminModel

if TYPE_CHECKING:
    from app.web.app import Application


class AdminAccessor(BaseAccessor):
    async def connect(
        self,
        app: "Application",
    ) -> None:
        base_admin = await self.get_by_email(email=app.config.admin.email)
        if base_admin is None:
            await self.create_admin(
                email=app.config.admin.email,
                password=app.config.admin.password,
            )

    async def get_by_email(self, email: str) -> AdminModel | None:
        async with self.app.database.session() as session:
            return await session.scalar(
                select(AdminModel).where(AdminModel.email == email)
            )

    async def create_admin(self, email: str, password: str) -> AdminModel:
        admin = AdminModel(
            email=email,
            password=str(hashlib.sha256(password.encode("utf-8")).hexdigest()),
        )
        async with self.app.database.session() as session:
            session.add(admin)
            await session.commit()
        return admin
