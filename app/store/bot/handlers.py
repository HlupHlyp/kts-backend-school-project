import enum
import typing, random

from sqlalchemy.ext.asyncio import AsyncSession

from app.blackjack.models import GameSessionStatus, ParticipantStatus
from app.store.tg_api.dataclasses import UpdateObj
from app.store.bot.dataclasses import Cards, Card, CardName, CardSuit

if typing.TYPE_CHECKING:
    from app.store.bot.manager import BotManager


class ReplyTemplate(enum.StrEnum):
    PLAYER_NUM_SETTING = "PLAYER_NUM_SETTING"
    INVITING = "INVITING"
    STARTING_GAME = "STARTING_GAME"
    STOPPING_GAME = "STOPPING_GAME"
    SESSION_ALREADY_STARTED = "SESSION_ALREADY_STARTED"


def get_card() -> Card:
    suit = random.choice(list(CardSuit))
    name = random.choice(list(CardName))
    weight = None
    print(suit, name)
    if name.value in (
        CardName.QUEEN.value,
        CardName.KING.value,
        CardName.JACK.value,
        CardName.TEN.value,
    ):
        weight = 10
        print(CardName.QUEEN.value)
        print
    elif name == CardName.ACE:
        weight = 11
        print("!!")
    else:
        weight = int(name.value)
        print("!!!")
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
    print(cost)
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
            chat_id=chat_id,
            status=GameSessionStatus.WAITING_FOR_NUM,
            session=session,
        )
        await manager.send_reply(
            chat_id=chat_id, reply_name=ReplyTemplate.PLAYER_NUM_SETTING
        )
    await session.commit()


async def stop_handler(
    manager: "BotManager", update: UpdateObj, session: AsyncSession
) -> None:
    chat_id = update.chat_id
    reply_name = ReplyTemplate.STOPPING_GAME
    await manager.send_reply(chat_id=chat_id, reply_name=reply_name)


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
            chat_id=chat_id, users_num=users_num, session=session
        )
        await manager.blackjack.set_game_session_status(
            chat_id=chat_id,
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
    if participant.status == ParticipantStatus.SLEEPING:
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
        game_session = await manager.blackjack.get_game_session_for_update(
            chat_id=chat_id, session=session
        )
        enough_gathered = await manager.blackjack.is_participants_gathered(
            game_session=game_session, session=session
        )
        if enough_gathered and GameSessionStatus.WAITING_FOR_USERS:
            await manager.send_message(
                text="Маршрутка полная. Поехали!",
                chat_id=chat_id,
            )
            participants = manager.blackjack.get_participants_for_update(
                session=session, game_session=game_session
            )
            for participant in participants:
                cards_set = []
                cards_set.append(get_card())
                cards_set.append(get_card())
                cards = Cards(cards=cards_set)

                await manager.send_message(
                    text=f"{participant.player.username}: {print_cards(cards)}",
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
                text=f"Карты дилера: {print_cards(cards)}",
                chat_id=chat_id,
            )
            await manager.blackjack.set_game_session_status(
                chat_id=chat_id,
                status=GameSessionStatus.POLLING,
                session=session,
            )
            await manager.blackjack.set_dealer_cards(
                game_session=game_session,
                cards=cards,
                session=session,
            )
            await manager.blackjack.set_participant_cards(
                participant=participant,
                cards=cards,
                session=session,
            )
            participant = next(
                participant
                for participant in participants
                if participant.status == ParticipantStatus.ACTIVE
            )
            await manager.blackjack.set_participant_status(
                participant=participant,
                session=session,
                status=ParticipantStatus.POLLING,
            )
            await manager.send_message(
                text=f"{participant.player.username}, ваш ход",
                chat_id=chat_id,
            )
            await manager.send_reply("get_card_or_enough", chat_id=chat_id)
            await session.commit()


async def get_card_handler(manager: "BotManager", update: UpdateObj) -> None:
    chat_id = update.callback_query.message.chat.id
    tg_id = update.callback_query.from_.id
    username = update.callback_query.from_.username
    async with manager.app.database.session() as session:
        participant = await manager.blackjack.get_participant_by_tg_and_chat_id(
            tg_id=tg_id, chat_id=chat_id, session=session
        )
        if participant.status == ParticipantStatus.POLLING:
            cards = await manager.blackjack.get_participant_cards(
                participant_id=participant.id, session=session
            )
            card = get_card()
            await manager.send_message(
                text=f"{card.name.value}{card.suit.value}",
                chat_id=chat_id,
            )
            cards.cards.append(card)
            await manager.blackjack.set_participant_cards(
                participant_id=participant.id, session=session, cards=cards
            )
            await session.commit()
            if get_cards_cost(cards) > 21:
                await manager.send_message(
                    text=f"{username}, Немного перебрал",
                    chat_id=chat_id,
                )


async def enough_handler(manager: "BotManager", update: UpdateObj) -> None:
    chat_id = update.callback_query.message.chat.id
    tg_id = update.callback_query.from_.id
    flag = False
    async with manager.app.database.session() as session:
        participant = await manager.blackjack.get_participant_by_tg_and_chat_id(
            tg_id=tg_id, chat_id=chat_id, session=session
        )
        if participant.status == ParticipantStatus.POLLING:
            flag = True
            await manager.blackjack.set_participant_status(
                participant_id=participant.id,
                status=ParticipantStatus.ASSEMBLED,
                session=session,
            )
        await session.commit()
    async with manager.app.database.session() as session:
        if flag:
            game_session = await manager.blackjack.check_game_session(
                chat_id=chat_id, session=session
            )
            try:
                new_poll_participant = next(
                    participant
                    for new_poll_participant in game_session.participants
                    if new_poll_participant.status == ParticipantStatus.ACTIVE
                )
            except StopIteration:
                await manager.blackjack.set_game_session_status(
                    chat_id=chat_id,
                    status=GameSessionStatus.SLEEPING,
                    session=session,
                )

            else:
                await manager.blackjack.set_participant_status(
                    participant_id=new_poll_participant.id,
                    status=ParticipantStatus.POLLING,
                    session=session,
                )
                await manager.send_message(
                    text=f"{new_poll_participant.player.username}, ваш ход",
                    chat_id=chat_id,
                )
                await manager.send_reply("get_card_or_enough", chat_id=chat_id)
            await session.commit()
