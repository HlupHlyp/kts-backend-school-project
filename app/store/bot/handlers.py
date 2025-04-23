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


JACK_COEF = 3
WIN_COEF = 2
LOSS_COEF = 0


CARDS_WEIGHTS: dict[CardName, int] = {
    CardName.ACE: 11,
    CardName.QUEEN: 10,
    CardName.KING: 10,
    CardName.JACK: 10,
    CardName.TEN: 10,
    CardName.NINE: 9,
    CardName.EIGHT: 8,
    CardName.SEVEN: 7,
    CardName.SIX: 6,
    CardName.FIVE: 5,
    CardName.FOUR: 4,
    CardName.THREE: 3,
    CardName.TWO: 2,
    CardName.ONE: 1,
}


def get_card() -> Card:
    suit = random.choice(list(CardSuit))
    name = random.choice(list(CardName))
    weight = CARDS_WEIGHTS[name]
    return Card(suit=suit, name=CardName(name), weight=weight)


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
    num_users = int(update.callback_query.data.split("/")[1])
    reply_name = ReplyTemplate.INVITING
    game_session = await manager.blackjack.get_game_session_for_update(
        chat_id=chat_id, session=session
    )
    if game_session.status == GameSessionStatus.WAITING_FOR_NUM:
        await manager.blackjack.set_game_session_users_num(
            game_session=game_session, num_users=num_users, session=session
        )
        await manager.blackjack.set_game_session_status(
            game_session=game_session,
            status=GameSessionStatus.WAITING_FOR_USERS,
            session=session,
        )
        await session.commit()
        await manager.send_message(
            chat_id=chat_id, text=f"Число участников: {num_users}"
        )
        await manager.send_reply(chat_id=chat_id, reply_name=reply_name)
    else:
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

    if not (
        participant.status == ParticipantStatus.SLEEPING
        and game_session.status == GameSessionStatus.WAITING_FOR_USERS
    ):
        return

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
        text=f" {participant.player.username} поставил: {bet}🟡 "
        f"(баланс: {participant.player.balance})",
    )
    await session.commit()
    enough_gathered = await manager.blackjack.is_participants_gathered(
        game_session=game_session, session=session
    )

    if not (enough_gathered and GameSessionStatus.WAITING_FOR_USERS):
        return

    await manager.send_message(
        text="Маршрутка полная. Поехали!",
        chat_id=chat_id,
    )
    participants = await manager.blackjack.get_participants_for_update(
        session=session, game_session=game_session
    )
    for participant in participants:
        if participant.status == ParticipantStatus.ACTIVE:
            cards = Cards([get_card(), get_card()])

            await manager.send_message(
                text=f"{participant.player.username}:{cards}",
                chat_id=chat_id,
            )
            await manager.blackjack.set_participant_cards(
                participant=participant,
                cards=cards,
                session=session,
            )

    cards = Cards([get_card(), get_card()])
    await manager.send_message(
        text=f"Дилер: \n {cards}",
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
    await switch_poll_participant(
        manager=manager, game_session=game_session, session=session
    )


async def get_card_handler(
    manager: "BotManager", update: UpdateObj, session: AsyncSession
) -> None:
    chat_id = update.chat_id
    tg_id = update.tg_id
    username = update.username
    participant = await manager.blackjack.get_participant_for_update(
        tg_id=tg_id, chat_id=chat_id, session=session
    )
    if not participant.is_polling:
        return
    cards = Cards.Schema().load(participant.right_hand)
    card = get_card()
    await manager.send_message(
        text=f"{card}",
        chat_id=chat_id,
    )
    cards.add_card(card)
    await manager.blackjack.set_participant_cards(
        participant=participant, session=session, cards=cards
    )
    cards_cost = cards.get_cost()
    if cards_cost > 21:
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
            await final_calculating(
                manager=manager, game_session=game_session, session=session
            )
    elif cards_cost == 21:
        game_session = await manager.blackjack.get_game_session_for_update(
            chat_id=chat_id, session=session
        )
        await manager.send_message(
            text=f"{participant.player.username} у тебя BlackJack",
            chat_id=chat_id,
        )
        await change_balance_on_bet_amount(
            manager=manager,
            session=session,
            participant=participant,
            game_session=game_session,
            coef=JACK_COEF,
        )
        await manager.blackjack.set_participant_status(
            participant=participant,
            status=ParticipantStatus.ASSEMBLED,
            session=session,
        )
        try:
            await switch_poll_participant(
                manager=manager, game_session=game_session, session=session
            )
        except NoActiveParticipantsError:
            await final_calculating(
                manager=manager, game_session=game_session, session=session
            )
    await session.commit()


async def enough_handler(
    manager: "BotManager", update: UpdateObj, session: AsyncSession
) -> None:
    chat_id = update.callback_query.message.chat.id
    tg_id = update.callback_query.from_.id
    participant = await manager.blackjack.get_participant_for_update(
        tg_id=tg_id, chat_id=chat_id, session=session
    )
    if not participant.is_polling:
        return
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
        await final_calculating(
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


async def final_calculating(
    manager: "BotManager", game_session: GameSessionModel, session: AsyncSession
) -> None:
    participants = await manager.blackjack.get_participants_for_update(
        game_session=game_session, session=session
    )
    manager.logger.info("final_calculating")
    dealer_cards = await dealer_finishing(
        manager=manager, game_session=game_session
    )
    dealer_cards_cost = dealer_cards.get_cost()

    await manager.send_message(
        text="СОБРАННЫЕ СЕТЫ",
        chat_id=game_session.chat_id,
    )

    for participant in participants:
        await manager.send_message(
            text=f"{participant.player.username}: "
            f"{Cards.Schema().load(participant.right_hand)} ",
            chat_id=game_session.chat_id,
        )

    participants = await manager.blackjack.get_participants_for_update(
        game_session=game_session, session=session
    )

    await manager.send_message(
        text=f"Дилер: {dealer_cards}",
        chat_id=game_session.chat_id,
    )
    # Проверяем не перербрал ли дилер

    if dealer_cards_cost > 21:
        # Если перебрал, то просто раздаем вознаграждения
        for participant in participants:
            await change_balance_on_bet_amount(
                manager=manager,
                participant=participant,
                game_session=game_session,
                session=session,
                coef=WIN_COEF,
            )
    else:
        # Если не перебрал, то сравниваем стоимость карт каждого из игроков
        # На этом основании определяем выигрыш или проигрыш
        for participant in participants:
            participant_cards_cost = (
                Cards.Schema().load(participant.right_hand).get_cost()
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
                    coef=WIN_COEF,
                )
            else:
                await change_balance_on_bet_amount(
                    manager=manager,
                    participant=participant,
                    game_session=game_session,
                    session=session,
                    coef=LOSS_COEF,
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
    if coef != LOSS_COEF:
        await manager.blackjack.change_balance_on_bet_amount(
            participant=participant, session=session, coef=coef
        )
    sign = ""
    action = participant.bet * coef
    if coef > 0:
        sign = "+"
    elif coef == 0:
        action = participant.bet * -1

    await manager.send_message(
        text=f"{participant.player.username}: {sign}{action} "
        f"(баланс: {participant.player.balance})",
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


async def dealer_finishing(
    manager: "BotManager", game_session: GameSessionModel
) -> Cards:
    dealer_cards = Cards.Schema().load(game_session.dealer_cards)
    await manager.send_message(
        text="Ход дилера:",
        chat_id=game_session.chat_id,
    )
    # Дораздаем карты дилеру
    while dealer_cards.get_cost() < 17:
        card = get_card()
        await manager.send_message(
            text=f"{card}",
            chat_id=game_session.chat_id,
        )
        dealer_cards.add_card(card)

    if dealer_cards.get_cost() > 21:
        await manager.send_message(
            text="Дилер немного перебрал",
            chat_id=game_session.chat_id,
        )
    return dealer_cards
