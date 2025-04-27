import typing

if typing.TYPE_CHECKING:
    from app.web.app import Application


def setup_routes(app: "Application"):
    from app.blackjack.views import GiveMoneyView, MoneyRatingView

    app.router.add_view("/blackjack.give_money", GiveMoneyView)
    app.router.add_view("/blackjack.money_rating", MoneyRatingView)
