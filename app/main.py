import asyncio
import datetime
import os
import time
from logging import Logger

import schedule
from dotenv import load_dotenv

from data_parser import Parser, ParserConfig
from data_processor import DataProcessor
from logging_config import LogConfig, LoggerSetup
from config import APIConfig, ScheduleSettings, PriceSettings, DataDirectories, Headers

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
    current_dir=os.path.abspath(DataDirectories.CURRENT_DATA_DIR),
    previous_dir=os.path.abspath(DataDirectories.PREVIOUS_DATA_DIR),
    changes_dir=os.path.abspath(DataDirectories.CHANGES_DATA_DIR),
)

parser = Parser(
    APIConfig.CATALOG_URL,
    APIConfig.PROXIES,
    data_processor,
    ParserConfig(
        PriceSettings.LOW_PRICE,
        PriceSettings.TOP_PRICE,
        PriceSettings.DISCOUNT,
    ),
)


async def scheduled_job() -> None:
    """Функция для выполнения запланированной работы"""
    try:
        data_processor.move_data_to_previous()
        await main()
        await data_processor.compare_and_save_changes(
            APIConfig.TOKEN,
            APIConfig.CHANNEL_IDS,
            APIConfig.PRICE_DIFFERENCE_PERCENTAGE,
        )
    except Exception as e:
        logger.error("Ошибка при выполнении запланированной работы: %s", e)


async def main() -> None:
    urls: list[str] = load_urls(os.path.abspath(DataDirectories.URLS_FILE_PATH))

    if not urls:
        logger.error("Список URL пуст.")
        return

    start: datetime.datetime = datetime.datetime.now()

    for url in urls[: ScheduleSettings.MAX_URLS_TO_PARSE]:
        await parser.run(
            Headers.HEADERS, url, ScheduleSettings.START_PAGE, ScheduleSettings.END_PAGE
        )

    end: datetime.datetime = datetime.datetime.now()
    total: datetime.timedelta = end - start

    logger.info("Затраченное время: %s", str(total))


def run_scheduled_job() -> None:
    asyncio.run(scheduled_job())


if __name__ == "__main__":
    run_scheduled_job()
    schedule.every(ScheduleSettings.SCHEDULE_INTERVAL).seconds.do(run_scheduled_job)

    while True:
        schedule.run_pending()
        time.sleep(1)
