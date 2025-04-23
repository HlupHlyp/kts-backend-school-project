import typing
from dataclasses import dataclass

import yaml

if typing.TYPE_CHECKING:
    from app.web.app import Application


@dataclass
class BotConfig:
    token: str
    num_workers: int


@dataclass
class AdminConfig:
    email: str
    password: str


@dataclass
class DatabaseConfig:
    host: str = "localhost"
    port: int = 5432
    user: str = "postgres"
    password: str = "postgres"
    database: str = "project"
    driver: str = "postgresql"


@dataclass
class Config:
    bot: BotConfig | None = None
    database: DatabaseConfig | None = None
    admin: AdminConfig | None = None


def setup_config(app: "Application", config_path: str):
    with open(config_path, "r") as f:
        raw_config = yaml.safe_load(f)

        app.config = Config(
            bot=BotConfig(**raw_config["bot"]),
            database=DatabaseConfig(**raw_config["database"]),
            admin=AdminConfig(
                **raw_config["admin"],
            ),
        )
