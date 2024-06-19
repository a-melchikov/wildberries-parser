import os
from typing import Optional, List
from logging import Logger
import requests
from logging_config import LoggerSetup, LogConfig

logger_setup = LoggerSetup(logger_name=__name__, log_config=LogConfig(filename=None))
logger: Logger = logger_setup.get_logger()

PROXIES: dict[str, str] = {"http": os.getenv("proxy")}
CATALOG_URL = "https://static-basket-01.wbbasket.ru/vol0/data/main-menu-ru-ru-v2.json"


class CatalogFetcher:
    @staticmethod
    def get_catalogs_wb() -> Optional[dict]:
        headers: dict[str, str] = {
            "Accept": "*/*",
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)",
        }
        try:
            response: requests.Response = requests.get(
                url=CATALOG_URL, headers=headers, proxies=PROXIES
            )
            response.raise_for_status()
            logger.info("Успешно получили данные каталога")
            return response.json()
        except requests.exceptions.HTTPError as http_err:
            logger.error("Произошла ошибка HTTP: %s", http_err)
        except requests.exceptions.RequestException as req_err:
            logger.error("Произошла ошибка запроса: %s", req_err)
        except ValueError as json_err:
            logger.error("Ошибка декодирования JSON: %s", json_err)
        return None

    @staticmethod
    def get_data_category(catalogs_wb: Optional[dict]) -> List[dict]:
        if not catalogs_wb:
            logger.warning("Не удалось получить данные каталога.")
            return []

        catalog_data = []
        if isinstance(catalogs_wb, dict):
            if "childs" not in catalogs_wb:
                catalog_data.append(
                    {
                        "name": catalogs_wb.get("name", "Неизвестная категория"),
                        "shard": catalogs_wb.get("shard"),
                        "url": catalogs_wb.get("url"),
                        "query": catalogs_wb.get("query"),
                    }
                )
            else:
                catalog_data.extend(
                    CatalogFetcher.get_data_category(catalogs_wb.get("childs", []))
                )
        else:
            for child in catalogs_wb:
                catalog_data.extend(CatalogFetcher.get_data_category(child))
        return catalog_data

    @staticmethod
    def search_category_in_catalog(
        url: str, catalog_list: List[dict]
    ) -> Optional[dict]:
        for catalog in catalog_list:
            if catalog["url"] == url.split("https://www.wildberries.ru")[-1]:
                logger.info("Найдено совпадение: %s", catalog["name"])
                return catalog
        logger.warning("Категория не найдена в каталоге.")
        return None
