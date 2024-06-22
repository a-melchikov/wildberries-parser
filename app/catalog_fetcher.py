from typing import Optional, List
from logging import Logger, getLogger
import requests

logger: Logger = getLogger(__name__)


class CatalogFetcher:
    def __init__(self, catalog_url: str, proxies: dict[str, str]) -> None:
        self.catalog_url: str = catalog_url
        self.proxies: dict[str, str] = proxies

    def get_catalogs_wb(self) -> Optional[dict]:
        headers: dict[str, str] = {
            "Accept": "*/*",
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)",
        }
        try:
            response: requests.Response = requests.get(
                url=self.catalog_url, headers=headers, proxies=self.proxies, timeout=10
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

    def get_data_category(self, catalogs_wb: Optional[dict]) -> List[dict]:
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
                    self.get_data_category(catalogs_wb.get("childs", []))
                )
        else:
            for child in catalogs_wb:
                catalog_data.extend(self.get_data_category(child))
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
