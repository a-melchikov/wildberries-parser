import os


def get_config() -> tuple[dict[str, str], str, list[str]]:
    proxies: dict[str, str] = {"http": os.getenv("proxy")}
    token: str | None = os.getenv("token")
    channel_ids: list[str] = os.getenv("channel_id").split(",")
    return proxies, token, channel_ids


PROXIES, TOKEN, CHANNEL_IDS = get_config()
CATALOG_URL = "https://static-basket-01.wbbasket.ru/vol0/data/main-menu-ru-ru-v2.json"
LOW_PRICE = 100
TOP_PRICE = 1000000
DISCOUNT = 30
