from logging import Logger, getLogger
from typing import Any
import asyncio
import aiohttp

from page_params import PageParams

logger: Logger = getLogger(__name__)


class DataFetcher:
    def __init__(self, proxies: dict[str, str], headers: dict[str, str]) -> None:
        self.proxies: dict[str, str] = proxies
        self.headers: dict[str, str] = headers

    async def scrap_page(self, page_params: PageParams) -> dict:
        """Сбор данных со страниц"""
        base_url: str = f"https://catalog.wb.ru/catalog/{page_params.shard}/catalog"
        query_params: dict[str, Any] = {
            "appType": 1,
            "curr": "rub",
            "dest": -1257786,
            "locale": "ru",
            "page": page_params.page,
            "priceU": f"{page_params.low_price * 100};{page_params.top_price * 100}",
            "sort": "popular",
            "spp": 0,
        }

        if page_params.discount is not None:
            query_params["discount"] = page_params.discount

        url: str = f"{base_url}?{page_params.query}&" + "&".join(
            [f"{key}={value}" for key, value in query_params.items()]
        )

        async with aiohttp.ClientSession() as session:
            try:
                for attempt in range(5):
                    async with session.get(
                        url=url,
                        headers=self.headers,
                        proxy=self.proxies.get("http"),
                        timeout=20,
                    ) as response:
                        if response.status == 200:
                            logger.info(
                                "Статус: %d Страница %d Идет сбор...",
                                response.status,
                                page_params.page,
                            )
                            return await response.json(content_type=None)
                        logger.warning(
                            "Попытка %d: неудачный статус %d для страницы %d",
                            attempt + 1,
                            response.status,
                            page_params.page,
                        )
                        await asyncio.sleep(1)

                logger.error(
                    "Не удалось получить данные со страницы %d после 5 попыток.",
                    page_params.page,
                )
                return {}

            except aiohttp.ClientError as e:
                logger.error("Ошибка соединения: %s", str(e))
                return {}

            except asyncio.TimeoutError:
                logger.error("Тайм-аут при запросе страницы %d", page_params.page)
                return {}
