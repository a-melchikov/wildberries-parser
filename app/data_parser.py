import asyncio
from dataclasses import dataclass
from logging import Logger, getLogger

from page_params import PageParams
from catalog_fetcher import CatalogFetcher
from data_fetcher import DataFetcher
from data_processor import DataProcessor

logger: Logger = getLogger(__name__)


@dataclass
class ParserConfig:
    """Конфигурация для парсера."""

    low_price: int = 1
    top_price: int = 1000000
    discount: int = 0


class Parser:
    def __init__(
        self,
        catalog_url: str,
        proxies: dict[str, str],
        data_processor: DataProcessor,
        config: ParserConfig,
    ) -> None:
        self.catalog_url: str = catalog_url
        self.proxies: dict[str, str] = proxies
        self.data_processor: DataProcessor = data_processor
        self.config: ParserConfig = config

    async def run(self, url: str, start_page: int = 1, end_page: int = 51) -> None:
        try:
            logger.info("Текущая конфигурация: %s", self.config)
            catalog_data = await self.fetch_catalog_data()
            if not catalog_data:
                logger.error("Не удалось получить данные каталога.")
                return

            category = self.get_category(url, catalog_data)
            if category is None:
                logger.error("Ошибка! Категория не найдена для URL: %s", url)
                return

            data_list = await self.fetch_data_pages(category, start_page, end_page)
            self.save_data(data_list, category, url)
        except TypeError as te:
            logger.error(
                "Ошибка! Возможно, неверно указан раздел. Удалите все доп фильтры с ссылки. Ошибка: %s",
                str(te),
            )
        except PermissionError as pe:
            logger.error(
                "Ошибка! Вы забыли закрыть созданный ранее файл. Закройте и повторите попытку. Ошибка: %s",
                str(pe),
            )
        except Exception as e:
            logger.error("Произошла непредвиденная ошибка: %s", str(e))

    async def fetch_catalog_data(self) -> list[dict]:
        """Получение данных каталога."""
        catalog_fetcher = CatalogFetcher(self.catalog_url, self.proxies)
        return catalog_fetcher.get_data_category(catalog_fetcher.get_catalogs_wb())

    def get_category(self, url: str, catalog_data: list[dict]) -> dict | None:
        """Поиск категории в каталоге по URL."""
        catalog_fetcher = CatalogFetcher(self.catalog_url, self.proxies)
        return catalog_fetcher.search_category_in_catalog(url, catalog_data)

    async def fetch_data_pages(
        self, category: dict, start_page: int, end_page: int
    ) -> list:
        """Асинхронный сбор данных со страниц."""
        data_fetcher = DataFetcher(self.proxies)
        tasks = [
            asyncio.create_task(
                data_fetcher.scrap_page(
                    PageParams(
                        page=page,
                        shard=category["shard"],
                        query=category["query"],
                        low_price=self.config.low_price,
                        top_price=self.config.top_price,
                        discount=self.config.discount,
                    )
                )
            )
            for page in range(start_page, end_page)
        ]
        result_list = await asyncio.gather(*tasks)
        data_list = []
        for data in result_list:
            page_data = self.data_processor.get_data_from_json(data)
            logger.info("Добавлено позиций: %d", len(page_data))
            if page_data:
                data_list.extend(page_data)
        logger.info("Сбор данных завершен. Собрано: %d товаров.", len(data_list))
        return data_list

    def save_data(self, data_list: list, category: dict, url: str) -> None:
        """Сохранение собранных данных и логирование итоговой информации."""
        file_name = f'{category["name"]}_from_{self.config.low_price}_to_{self.config.top_price}'
        self.data_processor.save_csv(data_list, file_name)
        logger.info(
            "Ссылка для проверки: %s?priceU=%d;%d&discount=%d",
            url,
            self.config.low_price * 100,
            self.config.top_price * 100,
            self.config.discount,
        )
