from logging import Logger
import os
import datetime
import time
from dotenv import load_dotenv
import schedule

from parser import Parser
from data_processor import DataProcessor
from logging_config import LogConfig, LoggerSetup


load_dotenv()
logger_setup = LoggerSetup(logger_name=__name__, log_config=LogConfig(filename=None))
logger: Logger = logger_setup.get_logger()

PROXIES: dict[str, str] = {
    "http": os.getenv("proxy"),
}
CATALOG_URL: str = (
    "https://static-basket-01.wbbasket.ru/vol0/data/main-menu-ru-ru-v2.json"
)

LOW_PRICE = 0
TOP_PRICE = 1000000
DISCOUNT = 10

data_processor = DataProcessor(
    current_dir="current_data", previous_dir="previous_data", changes_dir="changes_data"
)
parser = Parser(CATALOG_URL, PROXIES, data_processor, LOW_PRICE, TOP_PRICE, DISCOUNT)


def scheduled_job() -> None:
    """Функция для выполнения запланированной работы"""
    data_processor.move_data_to_previous()
    main()
    data_processor.compare_and_save_changes()


def main() -> None:
    urls: list[str] = [
        "https://www.wildberries.ru/catalog/zhenshchinam/odezhda/kostyumy",
        "https://www.wildberries.ru/catalog/obuv/detskaya/dlya-devochek",
        "https://www.wildberries.ru/catalog/obuv/detskaya/dlya-malchikov",
        "https://www.wildberries.ru/catalog/zhenshchinam/odezhda/bryuki-i-shorty",
        "https://www.wildberries.ru/catalog/zhenshchinam/odezhda/verhnyaya-odezhda",
        "https://www.wildberries.ru/catalog/zhenshchinam/odezhda/dzhempery-i-kardigany",
        "https://www.wildberries.ru/catalog/zhenshchinam/odezhda/dzhinsy-dzhegginsy",
    ]

    start: datetime.datetime = datetime.datetime.now()

    for url in urls:
        parser.run(url, 1, 31)

    end: datetime.datetime = datetime.datetime.now()
    total: datetime.timedelta = end - start

    logger.info("Затраченное время: %s", str(total))


if __name__ == "__main__":
    scheduled_job()
    schedule.every(1).minutes.do(scheduled_job)

    while True:
        schedule.run_pending()
        time.sleep(1)
