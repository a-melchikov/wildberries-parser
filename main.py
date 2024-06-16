import random
import time
import requests

HEADERS = {
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

BASE_URL = "https://catalog.wb.ru/catalog/electronic17/v2/catalog"
PARAMS = {
    "appType": 1,
    "cat": 60775,
    "curr": "rub",
    "dest": -1257786,
    "sort": "popular",
    "spp": 30
}
RETRY_LIMIT = 3

def fetch_page(url, params, headers):
    for attempt in range(RETRY_LIMIT):
        try:
            response = requests.get(url, headers=headers, params=params)
            response.raise_for_status()
            return response.json()
        except requests.RequestException as e:
            print(f"Ошибка при получении страницы {params['page']}: {e}")
            time.sleep(random.uniform(1, 3))
    return None

def parse_product(product, number):
    try:
        name = product.get("name", "Нет названия")
        brand = product.get("brand", "Нет бренда")
        price = product.get("sizes", [{}])[0].get("price", {}).get("total", 0)
        article = product.get("id", "Нет артикула")
        feedbacks = product.get("feedbacks", "Нет отзывов")
        review_rating = product.get("reviewRating", "Нет рейтинга")
        link = f"https://www.wildberries.ru/catalog/{article}/detail.aspx"

        print(f"ID: {number}")
        print(f"Название: {name}")
        print(f"Бренд: {brand}")
        print(f"Цена: {price / 100:.2f} руб.")
        print(f"Кол-во отзывов: {feedbacks}")
        print(f"Оценка: {review_rating}")
        print(f"Артикул: {article}")
        print(f"Ссылка: {link}")
        print("-" * 40)
    except Exception as e:
        print(f"Ошибка при парсинге продукта: {e}")

def main():
    number = 1
    for page in range(1, 100):
        params = PARAMS.copy()
        params["page"] = page
        data = fetch_page(BASE_URL, params, HEADERS)
        if not data:
            print(f"Ошибка при получении страницы {page}")
            continue
        products = data.get("data", {}).get("products", [])
        if not products:
            print(f"Товары не найдены на странице {page}")
            break
        for product in products:
            parse_product(product, number)
            number += 1

if __name__ == "__main__":
    main()
