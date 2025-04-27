import hashlib

from aiohttp.web_exceptions import HTTPBadRequest, HTTPForbidden
from aiohttp_apispec import (
    request_schema,
    response_schema,
)
from aiohttp_session import get_session, new_session

from app.admin.schemes import AdminRequestSchema, AdminSchema
from app.web.app import View
from app.web.mixins import AuthRequiredMixin
from app.web.utils import json_response


class AdminLoginView(View):
    @request_schema(AdminRequestSchema)
    @response_schema(AdminSchema, 200)
    async def post(self):
        """Просто логин админа"""
        data = await self.request.json()
        if "email" not in data:
            raise HTTPBadRequest
        admin = await self.store.admins.get_by_email(email=data["email"])
        if not admin:
            raise HTTPForbidden
        if admin.password != str(
            hashlib.sha256(data["password"].encode("utf-8")).hexdigest()
        ):
            raise HTTPForbidden
        session = await new_session(self.request)
        session["admin_email"] = admin.email
        return json_response(data={"id": admin.id, "email": admin.email})


class AdminLogoutView(AuthRequiredMixin, View):
    @response_schema(AdminSchema, 200)
    async def get(self):
        """Просто выхода админа"""
        session = await get_session(self.request)
        session["admin_email"] = None
        return json_response(data={"message": "Выход успешно осуществлен"})
