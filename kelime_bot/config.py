from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path


@dataclass(slots=True)
class MySQLConfig:
    host: str
    port: int
    user: str
    password: str
    database: str


@dataclass(slots=True)
class BotConfig:
    discord_token: str
    mysql: MySQLConfig
    word_list_dir: Path

    @classmethod
    def from_env(cls) -> "BotConfig":
        token = os.getenv("DISCORD_TOKEN", "").strip()
        if not token:
            raise ValueError("DISCORD_TOKEN bulunamadi. Lutfen .env dosyasini doldurun.")

        mysql = MySQLConfig(
            host=os.getenv("MYSQL_HOST", "127.0.0.1").strip(),
            port=int(os.getenv("MYSQL_PORT", "3306").strip()),
            user=os.getenv("MYSQL_USER", "root").strip(),
            password=os.getenv("MYSQL_PASSWORD", "").strip(),
            database=os.getenv("MYSQL_DATABASE", "kelime_botu").strip(),
        )

        project_root = Path(__file__).resolve().parent.parent
        list_dir_env = os.getenv("WORD_LIST_DIR", "Kelime-Listesi").strip()
        word_list_dir = Path(list_dir_env)
        if not word_list_dir.is_absolute():
            word_list_dir = (project_root / word_list_dir).resolve()

        return cls(discord_token=token, mysql=mysql, word_list_dir=word_list_dir)
