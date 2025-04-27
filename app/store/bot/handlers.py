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
from app.store.bot.exceptions import (
    NoActiveParticipantsError,
    PlayerNotFoundError,
)
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
    GET_RULES = "GET_RULES"


JACK_COEF = 2
WIN_COEF = 1
LOSS_COEF = -1


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
    if (
        game_session.status != GameSessionStatus.SLEEPING
        and not game_session.is_stopped
    ):
        await manager.send_reply(
            chat_id=chat_id,
            reply_name=ReplyTemplate.SESSION_ALREADY_STARTED,
        )
    else:
        await manager.blackjack.clear_session(
            session=session, game_session=game_session
        )
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
    firstname = update.firstname
    bet = int(update.callback_query.data.split("/")[1])
    participant = await manager.blackjack.get_or_create_participant(
        tg_id=tg_id,
        chat_id=chat_id,
        username=username,
        firstname=firstname,
        session=session,
    )
    game_session = await manager.blackjack.get_game_session_for_update(
        chat_id=chat_id, session=session
    )

    if (
        not (
            participant.status == ParticipantStatus.SLEEPING
            and game_session.status == GameSessionStatus.WAITING_FOR_USERS
        )
        or game_session.is_stopped
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
        text=f" {participant.player.name} поставил: {bet}🟡 "
        f"(баланс: {participant.player.balance})",
    )
    await session.commit()
    enough_gathered = await manager.blackjack.is_participants_gathered(
        game_session=game_session, session=session
    )

    if not (enough_gathered and GameSessionStatus.WAITING_FOR_USERS):
        return
    await primary_cards_distributing(
        manager=manager, game_session=game_session, session=session
    )


async def primary_cards_distributing(
    manager: "BotManager", game_session: GameSessionModel, session: AsyncSession
) -> None:
    messages = "Маршрутка полная. Поехали!"
    participants = await manager.blackjack.get_participants_for_update(
        session=session, game_session=game_session
    )
    for participant in participants:
        if participant.status == ParticipantStatus.ACTIVE:
            cards = Cards([get_card(), get_card()])

            messages += f"\n\n{participant.player.name}:{cards}"
            await manager.blackjack.set_participant_cards(
                participant=participant,
                cards=cards,
                session=session,
            )
            if cards.get_cost() == 21:
                messages += f"\nЭто BlackJack +{JACK_COEF * participant.bet} "
                messages += f"(баланс: {participant.player.balance})"
                await change_balance_on_bet_amount(
                    manager=manager,
                    session=session,
                    participant=participant,
                    coef=JACK_COEF,
                )
                await manager.blackjack.set_participant_status(
                    participant=participant,
                    status=ParticipantStatus.ASSEMBLED,
                    session=session,
                )
    cards = Cards([get_card(), get_card()])
    messages += f"\n\nДилер: \n{cards}"
    await manager.send_message(
        text=messages,
        chat_id=game_session.chat_id,
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
    participant = await manager.blackjack.get_participant_for_update(
        tg_id=tg_id, chat_id=chat_id, session=session
    )
    game_session = await manager.blackjack.get_game_session_for_update(
        chat_id=chat_id, session=session
    )
    if not participant.is_polling or game_session.is_stopped:
        return
    cards = Cards.from_dict(participant.right_hand)
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
            text=f"{participant.player.name}, Немного перебрал",
            chat_id=chat_id,
        )
        await manager.blackjack.set_participant_status(
            participant=participant,
            status=ParticipantStatus.ASSEMBLED,
            session=session,
        )
        await session.commit()

        try:
            await switch_poll_participant(
                manager=manager, game_session=game_session, session=session
            )
        except NoActiveParticipantsError:
            await final_calculating(
                manager=manager, game_session=game_session, session=session
            )
    elif cards_cost == 21:
        message = f"{participant.player.name} у тебя BlackJack"

        message += await change_balance_on_bet_amount(
            manager=manager,
            session=session,
            participant=participant,
            coef=JACK_COEF,
        )
        await manager.blackjack.set_participant_status(
            participant=participant,
            status=ParticipantStatus.ASSEMBLED,
            session=session,
        )
        await manager.send_message(
            text=message,
            chat_id=chat_id,
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


async def enough_handler(
    manager: "BotManager", update: UpdateObj, session: AsyncSession
) -> None:
    chat_id = update.callback_query.message.chat.id
    tg_id = update.callback_query.from_.id
    participant = await manager.blackjack.get_participant_for_update(
        tg_id=tg_id, chat_id=chat_id, session=session
    )
    game_session = await manager.blackjack.get_game_session_for_update(
        chat_id=chat_id, session=session
    )
    if not participant.is_polling or game_session.is_stopped:
        return
    await manager.blackjack.set_participant_status(
        participant=participant,
        status=ParticipantStatus.ASSEMBLED,
        session=session,
    )
    await session.commit()
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
        text=f"{new_poll_participant.player.name}, ваш ход",
        chat_id=game_session.chat_id,
    )
    await manager.send_reply(
        ReplyTemplate.GET_CARD_OR_ENOUGH, chat_id=game_session.chat_id
    )


async def final_calculating(
    manager: "BotManager", session: AsyncSession, game_session: GameSessionModel
) -> None:
    participants = await manager.blackjack.get_participants_for_update(
        game_session=game_session, session=session
    )
    manager.logger.info("final_calculating")
    dealer_cards = await dealer_finishing(
        manager=manager, session=session, game_session=game_session
    )
    dealer_cards_cost = dealer_cards.get_cost()
    messages = "СОБРАННЫЕ СЕТЫ"

    for participant in participants:
        messages += f" \n\n{participant.player.name}: "
        messages += f"{Cards.from_dict(participant.right_hand)} "

    participants = await manager.blackjack.get_participants_for_update(
        game_session=game_session, session=session
    )
    messages += f"\n \nДилер: {dealer_cards}"
    await manager.send_message(
        text=messages,
        chat_id=game_session.chat_id,
    )
    # Проверяем не перербрал ли дилер
    messages = ""
    if dealer_cards_cost > 21:
        # Если перебрал, то просто раздаем вознаграждения
        for participant in participants:
            messages += await change_balance_on_bet_amount(
                manager=manager,
                participant=participant,
                session=session,
                coef=WIN_COEF,
            )
    else:
        # Если не перебрал, то сравниваем стоимость карт каждого из игроков
        # На этом основании определяем выигрыш или проигрыш
        for participant in participants:
            participant_cards_cost = Cards.from_dict(
                participant.right_hand
            ).get_cost()
            if (
                participant_cards_cost > dealer_cards_cost
                and participant_cards_cost < 22
            ):
                messages += await change_balance_on_bet_amount(
                    manager=manager,
                    participant=participant,
                    session=session,
                    coef=WIN_COEF,
                )
            else:
                messages += await change_balance_on_bet_amount(
                    manager=manager,
                    participant=participant,
                    session=session,
                    coef=LOSS_COEF,
                )

            await manager.blackjack.set_participant_status(
                participant=participant,
                session=session,
                status=ParticipantStatus.SLEEPING,
            )
    await manager.send_message(
        text=messages,
        chat_id=game_session.chat_id,
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
    session: AsyncSession,
    coef: int,
) -> str:
    await manager.blackjack.change_balance_on_bet_amount(
        participant=participant, session=session, coef=coef
    )
    sign = ""
    action = participant.bet * coef
    if coef > 0:
        sign = "+"
    elif coef == 0:
        action = participant.bet * -1
    message = f"\n{participant.player.name}: {sign}{action} "
    message += f"(баланс: {participant.player.balance})"
    return message


async def stop_handler(
    manager: "BotManager", update: UpdateObj, session: AsyncSession
) -> None:
    chat_id = update.chat_id
    game_session = await manager.blackjack.get_game_session_for_update(
        session=session, chat_id=chat_id
    )
    message = "Нечего завершать. Сессия не активна"
    if (
        game_session.status != GameSessionStatus.SLEEPING
        and not game_session.is_stopped
    ):
        await manager.blackjack.set_game_session_stopped(
            session=session, game_session=game_session, is_stopped=True
        )
        message = "Игра насильно завершена"

    await manager.send_message(
        text=message,
        chat_id=game_session.chat_id,
    )
    await session.commit()


async def dealer_finishing(
    manager: "BotManager", session: AsyncSession, game_session: GameSessionModel
) -> Cards:
    dealer_cards = Cards.from_dict(game_session.dealer_cards)
    """Вынес отдельный handler для добора дилером карт"""
    messages = "Ход дилера: \n\n"

    # Дораздаем карты дилеру
    while dealer_cards.get_cost() < 17:
        card = get_card()
        messages += f"{card}"
        dealer_cards.add_card(card)

    if dealer_cards.get_cost() > 21:
        messages += "\n\nДилер немного перебрал"

    await manager.blackjack.set_dealer_cards(
        game_session=game_session,
        cards=dealer_cards,
        session=session,
    )
    await manager.send_message(
        text=messages,
        chat_id=game_session.chat_id,
    )
    return dealer_cards


async def get_balances_handler(
    manager: "BotManager", update: UpdateObj, session: AsyncSession
) -> None:
    game_session = await manager.blackjack.get_or_create_game_session(
        session=session, chat_id=update.chat_id
    )
    await session.commit()
    messages = ""
    try:
        players = await manager.blackjack.get_players(
            game_session=game_session, session=session
        )
    except PlayerNotFoundError:
        messages = (
            "Игроков, принимавших участие в игре данного чата не найдено."
        )
    else:
        for player in players:
            messages += f"Баланс {player.name}: {player.balance}\n\n"
    await manager.send_message(
        text=messages,
        chat_id=game_session.chat_id,
    )


async def get_prev_session_handler(
    manager: "BotManager", update: UpdateObj, session: AsyncSession
) -> None:
    game_session = await manager.blackjack.get_or_create_game_session(
        session=session, chat_id=update.chat_id
    )
    participants = list(
        await manager.blackjack.get_prev_session_participants(
            session=session, game_session=game_session
        )
    )
    messages = "Нет данных предыдущей сессии, поскольку начата новая"
    if game_session.is_stopped:
        messages = "Предыдущая сессия не была доиграна"
    elif (
        participants == [] and game_session.status == GameSessionStatus.SLEEPING
    ):
        messages = "В BlackJack в этом чате еще не играли"
    elif (
        game_session.status == GameSessionStatus.SLEEPING and participants != []
    ):
        dealer_cards = Cards.from_dict(game_session.dealer_cards)
        dealer_cards_cost = dealer_cards.get_cost()
        bets = "СТАВКИ"
        cards = f"\n\nСОБРАННЫЕ СЕТЫ\n\nДилер: {dealer_cards}"
        results = "\n\nРЕЗУЛЬТАТЫ"
        for participant in participants:
            participant_cards, coef = (
                Cards.from_dict(participant.right_hand),
                0,
            )
            bets += f"\n\n{participant.player.name} поставил: "
            bets += f" {participant.bet}🟡 "
            participant_cards_cost = participant_cards.get_cost()
            cards += f" \n\n{participant.player.name}: "
            cards += f"{participant_cards} "
            if participant_cards.get_cost() == 21:
                coef += JACK_COEF
            if (
                dealer_cards_cost > 21
                or dealer_cards_cost < participant_cards_cost < 22
            ):
                coef += WIN_COEF
            else:
                coef += LOSS_COEF
            results += f"\n\n{participant.player.name}: "
            results += f"{'+' if coef > 0 else ''}{coef * participant.bet}"
        messages = bets + cards + results
    await manager.send_message(
        text=messages,
        chat_id=game_session.chat_id,
    )


async def get_rules_handler(
    manager: "BotManager", update: UpdateObj, session: AsyncSession
) -> None:
    await manager.send_reply(
        reply_name=ReplyTemplate.GET_RULES, chat_id=update.chat_id
    )


async def continue_handler(
    manager: "BotManager", update: UpdateObj, session: AsyncSession
) -> None:
    game_session = await manager.blackjack.get_or_create_game_session(
        session=session, chat_id=update.chat_id
    )
    await manager.blackjack.set_game_session_stopped(
        session=session, game_session=game_session, is_stopped=False
    )
    if game_session.status == GameSessionStatus.SLEEPING:
        await manager.send_message(
            text="Предыдущая сессия была завершена успешно. Нечего продолжать",
            chat_id=game_session.chat_id,
        )
    elif game_session.status == GameSessionStatus.WAITING_FOR_NUM:
        await manager.send_reply(
            chat_id=game_session.chat_id,
            reply_name=ReplyTemplate.PLAYER_NUM_SETTING,
        )
    elif game_session.status == GameSessionStatus.WAITING_FOR_USERS:
        participants = list(
            await manager.blackjack.get_participants_for_update(
                session=session, game_session=game_session
            )
        )
        if len(participants) < game_session.num_users:
            bets = ""
            for participant in participants:
                bets += f"\n\n{participant.player.name} поставил: "
                bets += f" {participant.bet}🟡 "
            await manager.send_message(chat_id=game_session.chat_id, text=bets)
            await manager.send_reply(
                chat_id=game_session.chat_id,
                reply_name=ReplyTemplate.INVITING,
            )
        else:
            await primary_cards_distributing(
                manager=manager, game_session=game_session, session=session
            )
    elif game_session.status == GameSessionStatus.POLLING:
        participants = list(
            await manager.blackjack.get_participants_for_update(
                session=session, game_session=game_session
            )
        )
        assembled_participants = [
            participant
            for participant in participants
            if participant.is_assembled
        ]
        polling_participant = [
            participant
            for participant in participants
            if participant.is_polling
        ]
        messages = "СОБРАННЫЕ СЕТЫ"
        if polling_participant != []:
            await manager.send_message(
                text=f"{polling_participant[0].player.name}, ваш ход",
                chat_id=game_session.chat_id,
            )
            await manager.send_reply(
                ReplyTemplate.GET_CARD_OR_ENOUGH, chat_id=game_session.chat_id
            )
        elif len(assembled_participants) == len(participants):
            await final_calculating(
                manager=manager, session=session, game_session=game_session
            )
        else:
            await switch_poll_participant(
                manager=manager, game_session=game_session, session=session
            )
        for participant in assembled_participants:
            messages += f" \n\n{participant.player.name}: "
            messages += f"{Cards.from_dict(participant.right_hand)} "

    await session.commit()
