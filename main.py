import asyncio
import datetime
import os
import time
from logging import Logger

import schedule
from dotenv import load_dotenv

from app.data_parser import Parser, ParserConfig
from app.data_processor import DataProcessor
from app.logging_config import LogConfig, LoggerSetup
from app.config import (
    PROXIES,
    TOKEN,
    CHANNEL_IDS,
    CATALOG_URL,
    LOW_PRICE,
    TOP_PRICE,
    DISCOUNT,
)

load_dotenv()


def setup_logger() -> Logger:
    logger_setup = LoggerSetup(
        logger_name=__name__, log_config=LogConfig(filename=None)
    )
    return logger_setup.get_logger()


def load_urls(file_path: str) -> list[str]:
    urls: list = []
    if os.path.exists(file_path):
        with open(file_path, "r", encoding="utf-8") as file:
            for row in file:
                urls.append(row.strip())
    else:
        logger.error("Файл %s не найден", file_path)
    return urls


logger: Logger = setup_logger()


data_processor = DataProcessor(
    current_dir="current_data",
    previous_dir="previous_data",
    changes_dir="../changes_data",
)

parser = Parser(
    CATALOG_URL,
    PROXIES,
    data_processor,
    ParserConfig(
        LOW_PRICE,
        TOP_PRICE,
        DISCOUNT,
    ),
)


async def scheduled_job() -> None:
    """Функция для выполнения запланированной работы"""
    try:
        data_processor.move_data_to_previous()
        await main()
        await data_processor.compare_and_save_changes(TOKEN, CHANNEL_IDS)
    except Exception as e:
        logger.error("Ошибка при выполнении запланированной работы: %s", e)


async def main() -> None:
    urls: list[str] = load_urls("app/urls.txt")

    if not urls:
        logger.error("Список URL пуст.")
        return

    start: datetime.datetime = datetime.datetime.now()

    for url in urls[:5]:
        await parser.run(url, 1, 31)

    end: datetime.datetime = datetime.datetime.now()
    total: datetime.timedelta = end - start

    logger.info("Затраченное время: %s", str(total))


def run_scheduled_job() -> None:
    asyncio.run(scheduled_job())


if __name__ == "__main__":
    run_scheduled_job()
    schedule.every(1).minutes.do(run_scheduled_job)

    while True:
        schedule.run_pending()
        time.sleep(1)
