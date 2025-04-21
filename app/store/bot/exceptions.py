class BaseError(Exception):
    def __init__(self):
        self.msg = ""

    def __str__(self) -> str:
        return self.msg


class GameSessionNotFoundError(BaseError):
    def __init__(self, chat_id: int) -> None:
        self.msg = f"Сессия для чата '{chat_id}' не найдена"


class PlayerNotFoundError(BaseError):
    def __init__(self, tg_id: int) -> None:
        self.msg = f"Игрок c tg_id:'{tg_id}' не участвует в сессии"


class ParticipantNotFoundError(BaseError):
    def __init__(self, participant_id: int) -> None:
        self.msg = f"Участник c id:'{participant_id}' не существует"


class ReplyTemplateNotFoundError(BaseError):
    def __init__(self, reply_name: str) -> None:
        self.msg = f"Шаблон ответа с именем: {reply_name} не найден"


class CommandRouteNotFoundError(BaseError):
    def __init__(self, command_name: str) -> None:
        self.msg = f"Обработчик команды: {command_name} не найден"


class QueryRouteNotFoundError(BaseError):
    def __init__(self, command_name: str) -> None:
        self.msg = f"Обработчик для query: {command_name} не найден"
