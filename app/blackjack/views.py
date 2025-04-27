from aiohttp.web_exceptions import HTTPBadRequest
from aiohttp_apispec import querystring_schema, request_schema, response_schema

from app.blackjack.schemes import (
    ChatSchema,
    PlayerRequestSchema,
    PlayerSchema,
    PlayersListSchema,
)
from app.store.bot.exceptions import (
    PlayerNotFoundError,
)
from app.web.app import View
from app.web.mixins import AuthRequiredMixin
from app.web.utils import json_response


class GiveMoneyView(AuthRequiredMixin, View):
    @request_schema(PlayerRequestSchema)
    @response_schema(PlayerSchema, 200)
    async def put(self):
        """View, позволяющее положить изменить баланс игрока"""
        data = await self.request.json()
        username, amount = (
            data["username"],
            data["amount"],
        )
        try:
            await self.store.blackjack.top_up_balance(
                username=username, amount=amount
            )
        except PlayerNotFoundError as e:
            raise HTTPBadRequest from e
        return json_response(
            data={"message": f"Счет {username} пополнен на {amount}"}
        )


class MoneyRatingView(AuthRequiredMixin, View):
    """View, выдающее рейтинг игроков по балансу
    с возможностью фильтрации по чату.
    """

    @querystring_schema(ChatSchema)
    @response_schema(PlayersListSchema, 200)
    async def get(self):
        # data = await self.request.json()
        chat_id, num_players = None, None
        try:
            chat_id = int(self.request.query["chat_id"])
        except KeyError:
            pass
        try:
            num_players = int(self.request.query["num_players"])
        except KeyError:
            pass
        players = await self.store.blackjack.get_money_rating(
            chat_id, num_players
        )
        return json_response(
            data={
                "players": [PlayerSchema().dump(player) for player in players]
            }
        )
