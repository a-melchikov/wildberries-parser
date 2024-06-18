import os
import datetime
import requests
import pandas as pd
from retry import retry
from dotenv import load_dotenv

load_dotenv()

proxies = {
    'http': os.getenv('proxy'),
}
CATALOG_URL = "https://static-basket-01.wbbasket.ru/vol0/data/main-menu-ru-ru-v2.json"


def get_catalogs_wb() -> dict:
    """Получаем полный каталог Wildberries"""
    headers = {'Accept': '*/*', 'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)'}
    try:
        response = requests.get(CATALOG_URL, headers=headers, proxies=proxies)
        response.raise_for_status()
        print("Успешно получили данные каталога")
        return response.json()
    except requests.exceptions.HTTPError as http_err:
        print(f"Произошла ошибка HTTP: {http_err}")
    except requests.exceptions.RequestException as req_err:
        print(f"Произошла ошибка запроса: {req_err}")
    except ValueError as json_err:
        print(f"Ошибка декодирования JSON: {json_err}")
    return None


def get_data_category(catalogs_wb: dict) -> list:
    """Сбор данных категорий из каталога Wildberries"""
    if not catalogs_wb:
        print("Не удалось получить данные каталога.")
        return []

    catalog_data = []
    if isinstance(catalogs_wb, dict):
        if 'childs' not in catalogs_wb:
            catalog_data.append({
                'name': catalogs_wb.get('name', 'Неизвестная категория'),
                'shard': catalogs_wb.get('shard'),
                'url': catalogs_wb.get('url'),
                'query': catalogs_wb.get('query'),
            })
        else:
            catalog_data.extend(get_data_category(catalogs_wb.get('childs', [])))
    else:
        for child in catalogs_wb:
            catalog_data.extend(get_data_category(child))
    return catalog_data


def search_category_in_catalog(url: str, catalog_list: list) -> dict:
    """Проверка пользовательской ссылки на наличие в каталоге"""
    for catalog in catalog_list:
        if catalog['url'] == url.split('https://www.wildberries.ru')[-1]:
            print(f"Найдено совпадение: {catalog['name']}")
            return catalog
    print("Категория не найдена в каталоге.")
    return None


def get_data_from_json(json_file: dict) -> list:
    """Извлекаем данные из JSON"""
    return [
        {
            'id': data.get('id'),
            'name': data.get('name'),
            'price': data.get('priceU', 0) // 100,
            'salePriceU': data.get('salePriceU', 0) // 100,
            'sale': data.get('sale'),
            'brand': data.get('brand'),
            'rating': data.get('rating'),
            'supplier': data.get('supplier'),
            'supplierRating': data.get('supplierRating'),
            'feedbacks': data.get('feedbacks'),
            'reviewRating': data.get('reviewRating'),
            'promoTextCard': data.get('promoTextCard'),
            'promoTextCat': data.get('promoTextCat'),
            'link': f'https://www.wildberries.ru/catalog/{data.get("id")}/detail.aspx?targetUrl=BP'
        }
        for data in json_file.get('data', {}).get('products', [])
    ]


@retry(Exception, tries=3, delay=1)
def scrap_page(session: requests.Session, page: int, shard: str, query: str, low_price: int, top_price: int, discount: int = None) -> dict:
    """Сбор данных со страниц"""
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:109.0) Gecko/20100101 Firefox/113.0",
        "Accept": "*/*",
        "Accept-Language": "ru-RU,ru;q=0.8,en-US;q=0.5,en;q=0.3",
        "Accept-Encoding": "gzip, deflate, br",
        "Origin": "https://www.wildberries.ru",
        'Content-Type': 'application/json; charset=utf-8',
        'Transfer-Encoding': 'chunked',
        "Connection": "keep-alive",
        'Vary': 'Accept-Encoding',
        'Content-Encoding': 'gzip',
        "Sec-Fetch-Dest": "empty",
        "Sec-Fetch-Mode": "cors",
        "Sec-Fetch-Site": "cross-site"
    }

    base_url = f'https://catalog.wb.ru/catalog/{shard}/catalog'
    params = {
        'appType': 1,
        'curr': 'rub',
        'dest': -1257786,
        'locale': 'ru',
        'page': page,
        'priceU': f'{low_price * 100};{top_price * 100}',
        'sort': 'popular',
        'spp': 0
    }

    if discount is not None:
        params['discount'] = discount

    url = f"{base_url}?{query}&" + '&'.join([f"{key}={value}" for key, value in params.items()])

    response = session.get(url, headers=headers, proxies=proxies)
    print(f'Статус: {response.status_code} Страница {page} Идет сбор...')

    response.raise_for_status()
    return response.json()


def save_csv(data: list, filename: str):
    """Сохранение результата в CSV файл"""
    df = pd.DataFrame(data)
    df.to_csv(f'{filename}.csv', index=False)
    print(f'Все сохранено в {filename}.csv\n')


def parser(url: str, low_price: int = 1, top_price: int = 1000000, discount: int = 0):
    """Основная функция"""
    catalog_data = get_data_category(get_catalogs_wb())
    if not catalog_data:
        return

    try:
        category = search_category_in_catalog(url=url, catalog_list=catalog_data)
        if category is None:
            print('Ошибка! Категория не найдена.')
            return

        data_list = []
        with requests.Session() as session:
            for page in range(1, 51):
                data = scrap_page(
                    session=session,
                    page=page,
                    shard=category['shard'],
                    query=category['query'],
                    low_price=low_price,
                    top_price=top_price,
                    discount=discount
                )
                page_data = get_data_from_json(data)
                print(f'Добавлено позиций: {len(page_data)}')
                if page_data:
                    data_list.extend(page_data)
                else:
                    break
        print(f'Сбор данных завершен. Собрано: {len(data_list)} товаров.')
        save_csv(data_list, f'{category["name"]}_from_{low_price}_to_{top_price}')
        print(f'Ссылка для проверки: {url}?priceU={low_price * 100};{top_price * 100}&discount={discount}')
    except TypeError:
        print('Ошибка! Возможно, неверно указан раздел. Удалите все доп фильтры с ссылки.')
    except PermissionError:
        print('Ошибка! Вы забыли закрыть созданный ранее файл. Закройте и повторите попытку.')
    except Exception as e:
        print(f'Произошла непредвиденная ошибка: {str(e)}')


def main():
    urls = [
        'https://www.wildberries.ru/catalog/zhenshchinam/odezhda/kostyumy',
        'https://www.wildberries.ru/catalog/obuv/detskaya/dlya-devochek',
        'https://www.wildberries.ru/catalog/obuv/detskaya/dlya-malchikov',
    ]
    low_price = 0
    top_price = 1000000
    discount = 10
    for url in urls:
        start = datetime.datetime.now()
        parser(url=url, low_price=low_price, top_price=top_price, discount=discount)
        end = datetime.datetime.now()
        total = end - start
        print("Затраченное время: " + str(total))


if __name__ == '__main__':
    main()
