from concurrent.futures._base import Future
import os
import datetime
from logging import (
    Logger,
    getLogger,
    basicConfig,
    DEBUG,
    FileHandler,
    StreamHandler,
    INFO,
)
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Any
import requests
import pandas as pd
from retry import retry
from dotenv import load_dotenv


logger: Logger = getLogger(__name__)
FORMAT = "%(asctime)s : %(name)s : %(levelname)s : %(message)s"
file_handler = FileHandler("data.log")
file_handler.setLevel(DEBUG)
console = StreamHandler()
console.setLevel(INFO)
basicConfig(level=DEBUG, format=FORMAT, handlers=[file_handler, console])

load_dotenv()

PROXIES: dict[str, str] = {
    "http": os.getenv("proxy"),
}
CATALOG_URL: str = (
    "https://static-basket-01.wbbasket.ru/vol0/data/main-menu-ru-ru-v2.json"
)


def get_catalogs_wb() -> dict:
    """Получаем полный каталог Wildberries"""
    headers: dict[str, str] = {
        "Accept": "*/*",
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)",
    }
    try:
        response: requests.Response = requests.get(
            url=CATALOG_URL, headers=headers, proxies=PROXIES, timeout=10
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


def get_data_category(catalogs_wb: dict) -> list:
    """Сбор данных категорий из каталога Wildberries"""
    if not catalogs_wb:
        logger.warning("Не удалось получить данные каталога.")
        return []

    catalog_data: list = []
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
            catalog_data.extend(get_data_category(catalogs_wb.get("childs", [])))
    else:
        for child in catalogs_wb:
            catalog_data.extend(get_data_category(child))
    return catalog_data


def search_category_in_catalog(url: str, catalog_list: list) -> dict:
    """Проверка пользовательской ссылки на наличие в каталоге"""
    for catalog in catalog_list:
        if catalog["url"] == url.split("https://www.wildberries.ru")[-1]:
            logger.info("Найдено совпадение: %s", catalog["name"])
            return catalog
    logger.warning("Категория не найдена в каталоге.")
    return None


def get_data_from_json(json_file: dict) -> list:
    """Извлекаем данные из JSON"""
    return [
        {
            "id": data.get("id"),
            "name": data.get("name"),
            "price": data.get("priceU", 0) // 100,
            "salePriceU": data.get("salePriceU", 0) // 100,
            "sale": data.get("sale"),
            "brand": data.get("brand"),
            "rating": data.get("rating"),
            "supplier": data.get("supplier"),
            "supplierRating": data.get("supplierRating"),
            "feedbacks": data.get("feedbacks"),
            "reviewRating": data.get("reviewRating"),
            "promoTextCard": data.get("promoTextCard"),
            "promoTextCat": data.get("promoTextCat"),
            "link": f'https://www.wildberries.ru/catalog/{data.get("id")}/detail.aspx?targetUrl=BP',
        }
        for data in json_file.get("data", {}).get("products", [])
    ]


@retry(Exception, tries=-1, delay=0)
def scrap_page(
    session: requests.Session,
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
        "Transfer-Encoding": "chunked",
        "Connection": "keep-alive",
        "Vary": "Accept-Encoding",
        "Content-Encoding": "gzip",
        "Sec-Fetch-Dest": "empty",
        "Sec-Fetch-Mode": "cors",
        "Sec-Fetch-Site": "cross-site",
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

    response: requests.Response = session.get(url, headers=headers, proxies=PROXIES)
    logger.info("Статус: %d Страница %d Идет сбор...", response.status_code, page)

    response.raise_for_status()
    return response.json()


def save_csv(data: list, filename: str) -> None:
    """Сохранение результата в CSV файл"""
    df = pd.DataFrame(data)
    df.to_csv(f"data/{filename}.csv", index=False)
    logger.info("Все сохранено в %s.csv", filename)


def parser(
    url: str, low_price: int = 1, top_price: int = 1000000, discount: int = 0
) -> None:
    """Основная функция"""
    catalog_data: list = get_data_category(get_catalogs_wb())
    if not catalog_data:
        return

    try:
        category: dict = search_category_in_catalog(url=url, catalog_list=catalog_data)
        if category is None:
            logger.error("Ошибка! Категория не найдена.")
            return

        data_list: list = []
        with requests.Session() as session:
            for page in range(1, 51):
                data: dict = scrap_page(
                    session=session,
                    page=page,
                    shard=category["shard"],
                    query=category["query"],
                    low_price=low_price,
                    top_price=top_price,
                    discount=discount,
                )
                page_data: list = get_data_from_json(data)
                logger.info("Добавлено позиций: %d", len(page_data))
                if page_data:
                    data_list.extend(page_data)
                else:
                    break
        logger.info("Сбор данных завершен. Собрано: %d товаров.", len(data_list))
        save_csv(data_list, f'{category["name"]}_from_{low_price}_to_{top_price}')
        logger.info(
            "Ссылка для проверки: %s?priceU=%d;%d&discount=%d",
            url,
            low_price * 100,
            top_price * 100,
            discount,
        )
    except TypeError:
        logger.error(
            "Ошибка! Возможно, неверно указан раздел. Удалите все доп фильтры с ссылки."
        )
    except PermissionError:
        logger.error(
            "Ошибка! Вы забыли закрыть созданный ранее файл. Закройте и повторите попытку."
        )
    except Exception as e:
        logger.error("Произошла непредвиденная ошибка: %s", str(e))


def main() -> None:
    urls: list[str] = [
        "https://www.wildberries.ru/catalog/zhenshchinam/odezhda/kostyumy",
        "https://www.wildberries.ru/catalog/obuv/detskaya/dlya-devochek",
        "https://www.wildberries.ru/catalog/obuv/detskaya/dlya-malchikov",
        "https://www.wildberries.ru/catalog/zhenshchinam/odezhda/bryuki-i-shorty",
        "https://www.wildberries.ru/catalog/zhenshchinam/odezhda/verhnyaya-odezhda",
        "https://www.wildberries.ru/catalog/zhenshchinam/odezhda/dzhempery-i-kardigany",
        "https://www.wildberries.ru/catalog/zhenshchinam/odezhda/dzhinsy-dzhegginsy",
    ]
    low_price = 0
    top_price = 1000000
    discount = 10

    start: datetime.datetime = datetime.datetime.now()

    with ThreadPoolExecutor(max_workers=len(urls)) as executor:
        futures: list[Future[None]] = [
            executor.submit(parser, url, low_price, top_price, discount) for url in urls
        ]
        for future in as_completed(futures):
            future.result()

    end: datetime.datetime = datetime.datetime.now()
    total: datetime.timedelta = end - start
    logger.info("Затраченное время: %s", str(total))


if __name__ == "__main__":
    main()
