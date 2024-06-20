from logging import Logger
import os
import datetime
import time
import shutil
import requests
import pandas as pd
from dotenv import load_dotenv
import schedule
from logging_config import LogConfig, LoggerSetup
from catalog_fetcher import CatalogFetcher
from data_fetcher import DataFetcher

load_dotenv()
logger_setup = LoggerSetup(logger_name=__name__, log_config=LogConfig(filename=None))
logger: Logger = logger_setup.get_logger()

PROXIES: dict[str, str] = {
    "http": os.getenv("proxy"),
}
CATALOG_URL: str = (
    "https://static-basket-01.wbbasket.ru/vol0/data/main-menu-ru-ru-v2.json"
)

CURRENT_DATA_DIR = "current_data"
PREVIOUS_DATA_DIR = "previous_data"
CHANGES_DATA_DIR = "changes_data"


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


def save_csv(data: list, filename: str, directory: str = CURRENT_DATA_DIR) -> None:
    """Сохранение результата в CSV файл"""
    df = pd.DataFrame(data)
    file_path: str = os.path.join(directory, f"{filename}.csv")
    df.to_csv(file_path, index=False)
    logger.info("Все сохранено в %s", file_path)


def parser(
    url: str, low_price: int = 1, top_price: int = 1000000, discount: int = 0
) -> None:
    """Основная функция"""
    catalog_fetcher = CatalogFetcher(CATALOG_URL, PROXIES)
    catalog_data: list = catalog_fetcher.get_data_category(catalog_fetcher.get_catalogs_wb())
    if not catalog_data:
        return

    try:
        category: dict = catalog_fetcher.search_category_in_catalog(url=url, catalog_list=catalog_data)
        if category is None:
            logger.error("Ошибка! Категория не найдена.")
            return

        data_list: list = []
        data_fetcher = DataFetcher(PROXIES)
        for page in range(1, 51):
            data: dict = data_fetcher.scrap_page(
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


def move_data_to_previous() -> None:
    """Перемещение данных из current_data в previous_data"""
    if os.path.exists(CURRENT_DATA_DIR):
        if not os.path.exists(PREVIOUS_DATA_DIR):
            os.makedirs(PREVIOUS_DATA_DIR)
        for filename in os.listdir(CURRENT_DATA_DIR):
            shutil.move(
                os.path.join(CURRENT_DATA_DIR, filename),
                os.path.join(PREVIOUS_DATA_DIR, filename),
            )
        logger.info("Данные перемещены в %s", PREVIOUS_DATA_DIR)
    else:
        logger.warning("Каталог %s не существует", CURRENT_DATA_DIR)


def compare_and_save_changes() -> None:
    """Сравнение файлов и сохранение изменений"""
    if not os.path.exists(CHANGES_DATA_DIR):
        os.makedirs(CHANGES_DATA_DIR)

    columns_to_include = [
        "id",
        "name_current",
        "price_current",
        "salePriceU_current",
        "salePriceU_previous",
        "sale_current",
        "brand_current",
        "rating_current",
        "supplier_current",
        "supplierRating_current",
        "feedbacks_current",
        "reviewRating_current",
        "promoTextCard_current",
        "promoTextCat_current",
        "link_current",
    ]

    for current_file in os.listdir(CURRENT_DATA_DIR):
        current_filepath = os.path.join(CURRENT_DATA_DIR, current_file)
        previous_filepath = os.path.join(PREVIOUS_DATA_DIR, current_file)

        if os.path.exists(previous_filepath):
            current_df = pd.read_csv(current_filepath)
            previous_df = pd.read_csv(previous_filepath)

            merged_df = current_df.merge(
                previous_df, on="id", suffixes=("_current", "_previous")
            )

            def calculate_percent_change(current_price, previous_price):
                if previous_price == 0:
                    return float("inf") if current_price != 0 else 0
                return ((current_price - previous_price) / previous_price) * 100

            merged_df["percent_change"] = merged_df.apply(
                lambda row: calculate_percent_change(
                    row["salePriceU_current"], row["salePriceU_previous"]
                ),
                axis=1,
            )

            changes_df = merged_df[(merged_df["percent_change"] < -10)]

            if not changes_df.empty:
                changes_filepath = os.path.join(
                    CHANGES_DATA_DIR, f"changes_{current_file}"
                )
                changes_df = changes_df[columns_to_include]
                changes_df.columns = [
                    col.replace("_current", "") for col in changes_df.columns
                ]
                changes_df.to_csv(changes_filepath, index=False)
                logger.info("Изменения сохранены в %s", changes_filepath)

                message = ""
                for _, row in changes_df.iterrows():
                    send_telegram(
                        f"---------TEST---------"
                        f"{row['name']}\n"
                        f"Цена была: {row['salePriceU_previous']}\n"
                        f"Цена стала: {row['salePriceU']}\n"
                        f"Цена уменьшилась на {-calculate_percent_change(row["salePriceU"], row["salePriceU_previous"])}%\n"
                        f"Ссылка: {row['link']}\n"
                    )
            else:
                logger.info("Изменений не найдено для файла %s", current_file)
        else:
            logger.warning("Предыдущий файл для %s не найден", current_file)


def scheduled_job() -> None:
    """Функция для выполнения запланированной работы"""
    move_data_to_previous()
    main()
    compare_and_save_changes()


def send_telegram(text: str):
    token = os.getenv("token")
    url = "https://api.telegram.org/bot"
    channels_id = os.getenv("channel_id").split(",")
    url += token
    method = url + "/sendMessage"
    for channel_id in channels_id:
        r = requests.post(
            method, data={"chat_id": channel_id, "text": text, "parse_mode": "HTML"}
        )


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

    # with ThreadPoolExecutor(max_workers=len(urls)) as executor:
    #     futures: list[Future[None]] = [
    #         executor.submit(parser, url, low_price, top_price, discount) for url in urls
    #     ]
    #     for future in as_completed(futures):
    #         future.result()
    for url in urls:
        parser(url=url, low_price=low_price, top_price=top_price, discount=discount)
    end: datetime.datetime = datetime.datetime.now()
    total: datetime.timedelta = end - start
    logger.info("Затраченное время: %s", str(total))


if __name__ == "__main__":
    scheduled_job()
    schedule.every(1).minutes.do(scheduled_job)

    while True:
        schedule.run_pending()
        time.sleep(1)
