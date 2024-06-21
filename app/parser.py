import aiohttp
import asyncio
from logging import Logger, getLogger
from catalog_fetcher import CatalogFetcher
from data_fetcher import DataFetcher
from data_processor import DataProcessor

logger: Logger = getLogger(__name__)


class Parser:
    def __init__(
        self,
        catalog_url: str,
        proxies: dict[str, str],
        data_processor: DataProcessor,
        low_price: int = 1,
        top_price: int = 1000000,
        discount: int = 0,
    ) -> None:
        self.low_price: int = low_price
        self.top_price: int = top_price
        self.discount: int = discount
        self.proxies: dict[str, str] = proxies
        self.catalog_url: str = catalog_url
        self.data_processor: DataProcessor = data_processor

    async def run(self, url: str, start_page: int = 1, end_page: int = 51) -> None:
        catalog_fetcher = CatalogFetcher(self.catalog_url, self.proxies)
        catalog_data: list[dict] = catalog_fetcher.get_data_category(
            catalog_fetcher.get_catalogs_wb()
        )
        if not catalog_data:
            logger.error("Не удалось получить данные каталога.")
            return

        try:
            category: dict | None = catalog_fetcher.search_category_in_catalog(
                url, catalog_data
            )
            if category is None:
                logger.error("Ошибка! Категория не найдена для URL: %s", url)
                return

            data_list: list = []
            data_fetcher = DataFetcher(self.proxies)
            tasks = []
            for page in range(start_page, end_page):
                tasks.append(
                    asyncio.create_task(
                        data_fetcher.scrap_page(
                            page=page,
                            shard=category["shard"],
                            query=category["query"],
                            low_price=self.low_price,
                            top_price=self.top_price,
                            discount=self.discount,
                        )
                    )
                )
            result_list = await asyncio.gather(*tasks)
            for data in result_list:
                page_data: list = self.data_processor.get_data_from_json(data)
                logger.info("Добавлено позиций: %d", len(page_data))
                if page_data:
                    data_list.extend(page_data)

            logger.info("Сбор данных завершен. Собрано: %d товаров.", len(data_list))
            self.data_processor.save_csv(
                data_list,
                f'{category["name"]}_from_{self.low_price}_to_{self.top_price}',
            )
            logger.info(
                "Ссылка для проверки: %s?priceU=%d;%d&discount=%d",
                url,
                self.low_price * 100,
                self.top_price * 100,
                self.discount,
            )
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
