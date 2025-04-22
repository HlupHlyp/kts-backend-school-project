import enum
import random
import typing

from sqlalchemy.ext.asyncio import AsyncSession

from app.blackjack.models import (
    GameSessionModel,
    GameSessionStatus,
    ParticipantModel,
    ParticipantStatus,
)
from app.store.bot.dataclasses import Card, CardName, Cards, CardSuit
from app.store.bot.exceptions import NoActiveParticipantsError
from app.store.tg_api.dataclasses import UpdateObj

if typing.TYPE_CHECKING:
    from app.store.bot.manager import BotManager


class ReplyTemplate(enum.StrEnum):
    PLAYER_NUM_SETTING = "PLAYER_NUM_SETTING"
    INVITING = "INVITING"
    STARTING_GAME = "STARTING_GAME"
    STOPPING_GAME = "STOPPING_GAME"
    SESSION_ALREADY_STARTED = "SESSION_ALREADY_STARTED"
    GET_CARD_OR_ENOUGH = "GET_CARD_OR_ENOUGH"


def get_card() -> Card:
    suit = random.choice(list(CardSuit))
    name = random.choice(list(CardName))
    weight = None
    if name.value in (
        CardName.QUEEN.value,
        CardName.KING.value,
        CardName.JACK.value,
        CardName.TEN.value,
    ):
        weight = 10
    elif name == CardName.ACE:
        weight = 11
    else:
        weight = int(name.value)
    return Card(suit=suit, name=CardName(name), weight=weight)


def get_cards_cost(cards_set: Cards) -> int:
    ace_num, cost = 0, 0
    for card in cards_set.cards:
        if card.name == CardName.ACE:
            cost += 11
            ace_num += 1
        elif card.name.value in ("Король", "Королева", "Валет"):
            cost += 10
        else:
            cost += int(card.name.value)
    while cost > 21 and ace_num > 0:
        cost -= 10
    return cost


def print_cards(cards_set: Cards) -> str:
    message = ""
    for card in cards_set.cards:
        message += f"{card.name.value}{card.suit.value}"
        message += "  "
    return message


async def start_handler(
    manager: "BotManager", update: UpdateObj, session: AsyncSession
) -> None:
    chat_id = update.chat_id
    game_session = await manager.blackjack.get_or_create_game_session(
        chat_id=chat_id, session=session
    )
    if game_session.status != GameSessionStatus.SLEEPING:
        await manager.send_reply(
            chat_id=chat_id,
            reply_name=ReplyTemplate.SESSION_ALREADY_STARTED,
        )
    else:
        await manager.blackjack.set_game_session_status(
            game_session=game_session,
            status=GameSessionStatus.WAITING_FOR_NUM,
            session=session,
        )
        await manager.send_reply(
            chat_id=chat_id, reply_name=ReplyTemplate.PLAYER_NUM_SETTING
        )
    await session.commit()


async def players_num_handler(
    manager: "BotManager", update: UpdateObj, session: AsyncSession
) -> None:
    chat_id = update.chat_id
    users_num = int(update.callback_query.data.split("/")[1])
    reply_name = ReplyTemplate.INVITING
    game_session = await manager.blackjack.get_game_session_for_update(
        chat_id=chat_id, session=session
    )
    if game_session.status == GameSessionStatus.WAITING_FOR_NUM:
        await manager.blackjack.set_game_session_users_num(
            game_session=game_session, users_num=users_num, session=session
        )
        await manager.blackjack.set_game_session_status(
            game_session=game_session,
            status=GameSessionStatus.WAITING_FOR_USERS,
            session=session,
        )
        await manager.send_message(
            chat_id=chat_id, text=f"Число участников: {users_num}"
        )
        await manager.send_reply(chat_id=chat_id, reply_name=reply_name)
    await session.commit()


async def bet_handler(
    manager: "BotManager", update: UpdateObj, session: AsyncSession
) -> None:
    chat_id = update.chat_id
    tg_id = update.tg_id
    username = update.username
    bet = int(update.callback_query.data.split("/")[1])
    participant = await manager.blackjack.get_or_create_participant(
        tg_id=tg_id, chat_id=chat_id, username=username, session=session
    )
    game_session = await manager.blackjack.get_game_session_for_update(
        chat_id=chat_id, session=session
    )
    if (
        participant.status == ParticipantStatus.SLEEPING
        and game_session.status == GameSessionStatus.WAITING_FOR_USERS
    ):
        await manager.blackjack.set_participant_bet(
            participant=participant, bet=int(bet), session=session
        )
        await manager.blackjack.set_participant_status(
            participant=participant,
            status=ParticipantStatus.ACTIVE,
            session=session,
        )
        await manager.send_message(
            chat_id=chat_id,
            text=f" {participant.player.username} поставил: {bet}🟡",
        )
        await session.commit()
        enough_gathered = await manager.blackjack.is_participants_gathered(
            game_session=game_session, session=session
        )
        if enough_gathered and GameSessionStatus.WAITING_FOR_USERS:
            await manager.send_message(
                text="Маршрутка полная. Поехали!",
                chat_id=chat_id,
            )
            participants = await manager.blackjack.get_participants_for_update(
                session=session, game_session=game_session
            )
            for participant in participants:
                if participant.status == ParticipantStatus.ACTIVE:
                    cards_set = []
                    cards_set.append(get_card())
                    cards_set.append(get_card())
                    cards = Cards(cards=cards_set)

                    await manager.send_message(
                        text=f"{participant.player.username}:"
                        f"{print_cards(cards)}",
                        chat_id=chat_id,
                    )
                    await manager.blackjack.set_participant_cards(
                        participant=participant,
                        cards=cards,
                        session=session,
                    )

            cards_set = []

            cards_set.append(get_card())
            cards_set.append(get_card())

            cards = Cards(cards=cards_set)
            await manager.send_message(
                text=f"Дилер: \n {print_cards(cards)}",
                chat_id=chat_id,
            )
            await manager.blackjack.set_game_session_status(
                game_session=game_session,
                status=GameSessionStatus.POLLING,
                session=session,
            )
            await manager.blackjack.set_dealer_cards(
                game_session=game_session,
                cards=cards,
                session=session,
            )
            await session.commit()
            participants = await manager.blackjack.get_participants_for_update(
                session=session, game_session=game_session
            )
            game_session = await manager.blackjack.get_game_session_for_update(
                chat_id=chat_id, session=session
            )
            await switch_poll_participant(
                manager=manager, game_session=game_session, session=session
            )
            await session.commit()


async def get_card_handler(
    manager: "BotManager", update: UpdateObj, session: AsyncSession
) -> None:
    chat_id = update.callback_query.message.chat.id
    tg_id = update.callback_query.from_.id
    username = update.callback_query.from_.username
    participant = await manager.blackjack.get_participant_for_update(
        tg_id=tg_id, chat_id=chat_id, session=session
    )
    if participant.status == ParticipantStatus.POLLING:
        cards = Cards.Schema().load(participant.right_hand)
        card = get_card()
        await manager.send_message(
            text=f"{card.name.value}{card.suit.value}",
            chat_id=chat_id,
        )
        cards.cards.append(card)
        await manager.blackjack.set_participant_cards(
            participant=participant, session=session, cards=cards
        )
        if get_cards_cost(cards) > 21:
            await manager.send_message(
                text=f"{username}, Немного перебрал",
                chat_id=chat_id,
            )
            await manager.blackjack.set_participant_status(
                participant=participant,
                status=ParticipantStatus.ASSEMBLED,
                session=session,
            )
            await session.commit()
            game_session = await manager.blackjack.get_game_session_for_update(
                chat_id=chat_id, session=session
            )
            try:
                await switch_poll_participant(
                    manager=manager, game_session=game_session, session=session
                )
            except NoActiveParticipantsError:
                await final_calculation(
                    manager=manager, game_session=game_session, session=session
                )
                await session.commit()
        elif get_cards_cost(cards) == 21:
            manager.send_message(
                text=f"{participant.player.username} у тебя BlackJack",
                chat_id=game_session.chat_id,
            )
            await change_balance_on_bet_amount(
                manager=manager,
                session=session,
                participant=participant,
                game_session=game_session,
                coef=2,
            )
            await session.commit()
        await session.commit()


async def enough_handler(
    manager: "BotManager", update: UpdateObj, session: AsyncSession
) -> None:
    chat_id = update.callback_query.message.chat.id
    tg_id = update.callback_query.from_.id
    flag = False
    participant = await manager.blackjack.get_participant_for_update(
        tg_id=tg_id, chat_id=chat_id, session=session
    )
    if participant.status == ParticipantStatus.POLLING:
        flag = True
        await manager.blackjack.set_participant_status(
            participant=participant,
            status=ParticipantStatus.ASSEMBLED,
            session=session,
        )
    await session.commit()
    if flag:
        game_session = await manager.blackjack.get_game_session_for_update(
            chat_id=chat_id, session=session
        )
        try:
            await switch_poll_participant(
                manager=manager, game_session=game_session, session=session
            )
        except NoActiveParticipantsError:
            await final_calculation(
                manager=manager, game_session=game_session, session=session
            )
            await session.commit()


async def switch_poll_participant(
    manager: "BotManager", game_session: GameSessionModel, session: AsyncSession
) -> None:
    new_poll_participant = await manager.blackjack.switch_poll_participant(
        session=session, game_session=game_session
    )
    await session.commit()
    await manager.send_message(
        text=f"{new_poll_participant.player.username}, ваш ход",
        chat_id=game_session.chat_id,
    )
    await manager.send_reply(
        ReplyTemplate.GET_CARD_OR_ENOUGH, chat_id=game_session.chat_id
    )


async def final_calculation(
    manager: "BotManager", game_session: GameSessionModel, session: AsyncSession
) -> None:
    manager.logger.info("final_calculation")
    dealer_cards = Cards.Schema().load(game_session.dealer_cards)
    await manager.send_message(
        text="Ход дилера:",
        chat_id=game_session.chat_id,
    )
    # Дораздаем карты дилеру
    while get_cards_cost(dealer_cards) < 17:
        card = get_card()
        await manager.send_message(
            text=f"{card.name.value}{card.suit.value}",
            chat_id=game_session.chat_id,
        )
        dealer_cards.cards.append(card)

    if get_cards_cost(dealer_cards) > 21:
        await manager.send_message(
            text="Дилер немного перебрал",
            chat_id=game_session.chat_id,
        )

    participants = await manager.blackjack.get_participants_for_update(
        game_session=game_session, session=session
    )
    await manager.send_message(
        text="СОБРАННЫЕ СЕТЫ",
        chat_id=game_session.chat_id,
    )
    for participant in participants:
        await manager.send_message(
            text=f"{participant.player.username}:"
            f"{print_cards(Cards.Schema().load(participant.right_hand))}",
            chat_id=game_session.chat_id,
        )
    await session.commit()
    participants = await manager.blackjack.get_participants_for_update(
        game_session=game_session, session=session
    )
    await manager.send_message(
        text=f"Дилер: {print_cards(dealer_cards)}",
        chat_id=game_session.chat_id,
    )
    dealer_cards_cost = get_cards_cost(dealer_cards)
    # Проверяем не перербрал ли дилер
    if dealer_cards_cost > 21:
        # Если перебрал, то просто раздаем вознаграждения
        for participant in participants:
            await change_balance_on_bet_amount(
                manager=manager,
                participant=participant,
                game_session=game_session,
                session=session,
                coef=1,
            )
            await manager.send_message(
                text=f"{participant.player.username}: +{participant.bet}",
                chat_id=game_session.chat_id,
            )
    else:
        # Если не перебрал, то сравниваем стоимость карт каждого из игроков
        # На этом основании определяем выигрыш или проигрыш
        for participant in participants:
            participant_cards_cost = get_cards_cost(
                Cards.Schema().load(participant.right_hand)
            )
            if (
                participant_cards_cost > dealer_cards_cost
                and participant_cards_cost < 22
            ):
                await change_balance_on_bet_amount(
                    manager=manager,
                    participant=participant,
                    game_session=game_session,
                    session=session,
                    coef=1,
                )
            else:
                await change_balance_on_bet_amount(
                    manager=manager,
                    participant=participant,
                    game_session=game_session,
                    session=session,
                    coef=-1,
                )
            await manager.blackjack.set_participant_status(
                participant=participant,
                session=session,
                status=ParticipantStatus.SLEEPING,
            )
        # Засыпляем сессию
    await manager.blackjack.set_game_session_status(
        game_session=game_session,
        status=GameSessionStatus.SLEEPING,
        session=session,
    )
    await session.commit()


async def change_balance_on_bet_amount(
    manager: "BotManager",
    participant: ParticipantModel,
    game_session: GameSessionModel,
    session: AsyncSession,
    coef: int,
) -> None:
    if coef != -1:
        await manager.blackjack.change_balance_on_bet_amount(
            participant=participant, session=session, coef=coef
        )
    sign = "+"
    if coef < 0:
        sign = "-"
    await manager.send_message(
        text=f"{participant.player.username}: {sign}{participant.bet}",
        chat_id=game_session.chat_id,
    )


async def stop_handler(
    manager: "BotManager", update: UpdateObj, session: AsyncSession
):
    chat_id = update.chat_id
    game_session = await manager.blackjack.get_game_session_for_update(
        session=session, chat_id=chat_id
    )
    await manager.blackjack.set_game_session_status(
        session=session,
        game_session=game_session,
        status=GameSessionStatus.SLEEPING,
    )
    participants = await manager.blackjack.get_participants_for_update(
        game_session=game_session, session=session
    )
    for participant in participants:
        await manager.blackjack.set_participant_status(
            participant=participant,
            session=session,
            status=ParticipantStatus.SLEEPING,
        )
    await manager.send_message(
        text="Игра насильно завершена",
        chat_id=game_session.chat_id,
    )
    await session.commit()
