from dataclasses import dataclass


@dataclass
class PageParams:
    """Класс для хранения параметров страницы и фильтрации товаров."""

    page: int
    shard: str
    query: str
    low_price: int
    top_price: int
    discount: int | None = None
