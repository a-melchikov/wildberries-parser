from logging import Logger, getLogger
from typing import Any
import asyncio
import aiohttp

logger: Logger = getLogger(__name__)


class DataFetcher:
    def __init__(self, proxies: dict[str, str]) -> None:
        self.proxies: dict[str, str] = proxies

    async def scrap_page(
        self,
        page: int,
        shard: str,
        query: str,
        low_price: int,
        top_price: int,
        discount: int = None,
    ) -> dict:
        """Сбор данных со страниц"""
        headers: dict[str, str] = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:109.0) Gecko/20100101 Firefox/113.0",
            "Accept": "*/*",
            "Accept-Language": "ru-RU,ru;q=0.8,en-US;q=0.5,en;q=0.3",
            "Accept-Encoding": "gzip, deflate, br",
            "Origin": "https://www.wildberries.ru",
            "Content-Type": "application/json; charset=utf-8",
            "Connection": "keep-alive",
        }

        base_url: str = f"https://catalog.wb.ru/catalog/{shard}/catalog"
        params: dict[str, Any] = {
            "appType": 1,
            "curr": "rub",
            "dest": -1257786,
            "locale": "ru",
            "page": page,
            "priceU": f"{low_price * 100};{top_price * 100}",
            "sort": "popular",
            "spp": 0,
        }

        if discount is not None:
            params["discount"] = discount

        url: str = f"{base_url}?{query}&" + "&".join(
            [f"{key}={value}" for key, value in params.items()]
        )
        async with aiohttp.ClientSession() as session:
            async with session.get(
                url=url, headers=headers, proxy=self.proxies["http"]
            ) as response:
                logger.info(
                    "Статус: %d Страница %d Идет сбор...", response.status, page
                )
                for _ in range(5):
                    if response.status == 200:
                        break
                    await asyncio.sleep(1)
                    async with session.get(
                        url=url, headers=headers, proxy=self.proxies["http"]
                    ) as response:
                        pass

                if response.status != 200:
                    logger.error(
                        "Не удалось получить данные со страницы %d. Статус: %d",
                        page,
                        response.status,
                    )
                    return {}
                return await response.json(content_type=None)
