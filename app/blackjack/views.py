from json import JSONDecodeError

from aiohttp.web_exceptions import HTTPBadRequest
from aiohttp_apispec import (
    request_schema,
    response_schema,
)

from app.blackjack.schemes import (
    ChatSchema,
    PlayerRequestSchema,
    PlayerSchema,
    PlayersListSchema,
)
from app.store.bot.exceptions import (
    GameSessionNotFoundError,
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
        try:
            data = await self.request.json()
        except JSONDecodeError as e:
            raise HTTPBadRequest from e
        username, amount = (
            data["username"],
            data["amount"],
        )
        if username is None or amount is None:
            raise HTTPBadRequest
        try:
            int(amount)
        except Exception as e:
            raise HTTPBadRequest from e
        try:
            await self.store.blackjack.top_up_balance(
                username=username, amount=int(amount)
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

    @request_schema(ChatSchema)
    @response_schema(PlayersListSchema, 200)
    async def get(self):
        params = self.request.rel_url.query
        chat_id = None
        try:
            chat_id = int(params["chat_id"])
        except KeyError as e:
            raise HTTPBadRequest from e
        except ValueError:
            pass
        try:
            players = await self.store.blackjack.get_money_rating(chat_id)
        except GameSessionNotFoundError as e:
            raise HTTPBadRequest from e
        players = sorted(players, key=lambda player: player.balance)
        return json_response(
            data={
                "players": [PlayerSchema().dump(player) for player in players]
            }
        )
