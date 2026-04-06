from __future__ import annotations

import logging

from dotenv import load_dotenv

from kelime_bot.bot import KelimeBot
from kelime_bot.config import BotConfig
from kelime_bot.database import Database
from kelime_bot.word_bank import WordBank


def configure_logging() -> None:
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
    )


def main() -> None:
    load_dotenv()
    configure_logging()

    config = BotConfig.from_env()

    word_bank = WordBank(config.word_list_dir)
    word_bank.load()

    logging.getLogger(__name__).info("Kelime bankasi yuklendi: %s", word_bank.size)

    database = Database(config.mysql)
    bot = KelimeBot(db=database, word_bank=word_bank)
    bot.run(config.discord_token)


if __name__ == "__main__":
    main()
