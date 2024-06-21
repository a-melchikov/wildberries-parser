import asyncio
from logging import Logger
import os
import datetime
import time
from dotenv import load_dotenv
import schedule

from catalog_fetcher import CatalogFetcher
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
TOKEN: str = os.getenv("token")
CHANNEL_IDS: list[str] = os.getenv("channel_id").split(",")

LOW_PRICE = 0
TOP_PRICE = 1000000
DISCOUNT = 10

data_processor = DataProcessor(
	current_dir="../current_data",
	previous_dir="../previous_data",
	changes_dir="../changes_data",
)
parser = Parser(CATALOG_URL, PROXIES, data_processor, LOW_PRICE, TOP_PRICE, DISCOUNT)


async def scheduled_job() -> None:
	"""Функция для выполнения запланированной работы"""
	data_processor.move_data_to_previous()
	await main()
	data_processor.compare_and_save_changes(TOKEN, CHANNEL_IDS)


async def main() -> None:
	urls: list[str] = []
	with open("urls.txt", "r", encoding="utf-8") as file:
		for row in file:
			urls.append(row.strip())

	start: datetime.datetime = datetime.datetime.now()

	for url in urls:
		await parser.run(url, 1, 31)

	end: datetime.datetime = datetime.datetime.now()
	total: datetime.timedelta = end - start

	logger.info("Затраченное время: %s", str(total))


def run_scheduled_job():
	asyncio.run(scheduled_job())


if __name__ == "__main__":
	run_scheduled_job()
	schedule.every(1).minutes.do(run_scheduled_job)

	while True:
		schedule.run_pending()
		time.sleep(1)
