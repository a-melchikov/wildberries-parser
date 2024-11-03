import os


class APIConfig:
    PROXIES: dict[str, str] = {"http": os.getenv("proxy")}
    TOKEN: str = os.getenv("token")
    CHANNEL_IDS: list[str] = os.getenv("channel_id").split(",")
    CATALOG_URL: str = (
        "https://static-basket-01.wbbasket.ru/vol0/data/main-menu-ru-ru-v2.json"
    )
    PRICE_DIFFERENCE_PERCENTAGE: int | float = 30


class PriceSettings:
    LOW_PRICE: int = 100
    TOP_PRICE: int = 1000000
    DISCOUNT: int = 30


class DataDirectories:
    CURRENT_DATA_DIR: str = "current_data"
    PREVIOUS_DATA_DIR: str = "previous_data"
    CHANGES_DATA_DIR: str = "changes_data"
    URLS_FILE_PATH: str = "urls.txt"


class ScheduleSettings:
    SCHEDULE_INTERVAL: int = 15
    MAX_URLS_TO_PARSE: int = 50
    START_PAGE: int = 1
    END_PAGE: int = 31


class Headers:
    HEADERS: dict[str, str] = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:109.0) Gecko/20100101 Firefox/113.0",
        "Accept": "*/*",
        "Accept-Language": "ru-RU,ru;q=0.8,en-US;q=0.5,en;q=0.3",
        "Accept-Encoding": "gzip, deflate, br",
        "Origin": "https://www.wildberries.ru",
        "Content-Type": "application/json; charset=utf-8",
        "Connection": "keep-alive",
    }
