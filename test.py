import datetime
import asyncio
import random
import aiohttp
import requests
import pandas as pd
from retry import retry
from fake_useragent import UserAgent

ua = UserAgent()

HEADERS = {
	"User-Agent": ua.random,
	"Accept": "*/*",
	"Accept-Language": "ru-RU,ru;q=0.8,en-US;q=0.5,en;q=0.3",
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

CATALOG_URL = "https://static-basket-01.wbbasket.ru/vol0/data/main-menu-ru-ru-v2.json"


def get_catalogs_wb() -> dict:
	"""Получаем полный каталог Wildberries"""
	try:
		response = requests.get(CATALOG_URL, headers=HEADERS)
		response.raise_for_status()  # Проверка статус-кода
		response.encoding = 'utf-8'  # Устанавливаем правильную кодировку
		print("Успешно получили данные каталога")
		return response.json()  # Попытка декодировать JSON
	except requests.exceptions.HTTPError as http_err:
		print(f"Произошла ошибка HTTP: {http_err}")
	except requests.exceptions.RequestException as req_err:
		print(f"Произошла ошибка запроса: {req_err}")
	except ValueError as json_err:
		print(f"Ошибка декодирования JSON: {json_err}")
	return None


def get_data_category(catalogs_wb: dict) -> list:
	"""Сбор данных категорий из каталога Wildberries"""
	if catalogs_wb is None:
		print("Не удалось получить данные каталога.")
		return []

	catalog_data = []
	if isinstance(catalogs_wb, dict) and 'childs' not in catalogs_wb:
		catalog_data.append({
			'name': f"{catalogs_wb.get('name', 'Неизвестная категория')}",
			'shard': catalogs_wb.get('shard', None),
			'url': catalogs_wb.get('url', None),
			'query': catalogs_wb.get('query', None),
		})
	elif isinstance(catalogs_wb, dict):
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
	"""Извлекаем из json данные"""
	data_list = []
	if not json_file or 'data' not in json_file or 'products' not in json_file['data']:
		return data_list

	for data in json_file['data']['products']:
		data_list.append({
			'id': data.get('id'),
			'Наименование': data.get('name'),
			'Цена': int(data.get('priceU') / 100),
			'Цена со скидкой': int(data.get('salePriceU') / 100),
			'Скидка': data.get('sale'),
			'Бренд': data.get('brand'),
			'Рейтинг': data.get('rating'),
			'Продавец': data.get('supplier'),
			'Рейтинг продавца': data.get('supplierRating'),
			'Промо текст карточки': data.get('promoTextCard'),
			'Промо текст категории': data.get('promoTextCat'),
			'Ссылка': f"https://www.wildberries.ru/catalog/{data.get('id')}/detail.aspx?targetUrl=BP",
		})
	return data_list


def get_url(page: int, shard: str, query: str, low_price: int, top_price: int, discount: int = None):
	url = f"https://catalog.wb.ru/catalog/{shard}/catalog?appType=1&curr=rub" \
		  f"&dest=-971647" \
		  f"&locale=ru" \
		  f"&page={page}" \
		  f"&priceU={low_price * 100};{top_price * 100}" \
		  f"&sort=popular&spp=0" \
		  f"&{query}" \
		  f"&discount={discount}"
	return url


# @retry(Exception, tries=-1, delay=0)
async def scrap_page(page: int, shard: str, query: str, low_price: int, top_price: int, discount: int = None) -> dict:
	"""Сбор данных со страницы"""

	url = get_url(page, shard, query, low_price, top_price, discount)
	try:
		async with aiohttp.ClientSession() as session:
			HEADERS['User-Agent'] = ua.random
			response = await session.get(url=url)
			if response.status == 429:
				print(f"Too Many Requests: {url}")
				return await scrap_page(page, shard, query, low_price, top_price, discount)

			response.raise_for_status()
			response.encoding = 'utf-8'
			print(f"[+] Страница {page}")

			for _ in range(5):
				if response.status == 200:
					break
				response = await session.get(url=url)
			if response.status != 200:
				return {}
			return await response.json(content_type=None)

	except requests.exceptions.HTTPError as http_err:
		print(f"Произошла ошибка HTTP: {http_err}")
	except requests.exceptions.RequestException as req_err:
		print(f"Произошла ошибка запроса: {req_err}")
	except ValueError as json_err:
		print(f"Ошибка декодирования JSON: {json_err}")
	except Exception as e:
		print(e)
	return None


def save_excel(data: list, filename: str):
	"""Сохранение результата в excel файл"""
	df = pd.DataFrame(data)
	writer = pd.ExcelWriter(f"{filename}.xlsx", engine='xlsxwriter')
	df.to_excel(writer, sheet_name='data', index=False)
	widths = [10, 34, 8, 9, 4, 10, 5, 25, 10, 11, 13, 19, 19, 67]
	worksheet = writer.sheets['data']
	for i, width in enumerate(widths):
		worksheet.set_column(i, i, width)
	writer.close()
	print(f"Данные сохранены в {filename}.xlsx\n")


def get_total_count(page: int, shard: str, query: str, low_price: int, top_price: int, discount: int = None) -> int:
	url = get_url(page, shard, query, low_price, top_price, discount)
	response = requests.get(url=url, headers=HEADERS)
	return response.json().get('data').get('total', 0)


async def parser(url: str, low_price: int = 1, top_price: int = 1_000_000, discount: int = 0):
	"""Основная функция"""
	catalog_data = get_data_category(get_catalogs_wb())  # Получение данных по заданному каталогу
	if not catalog_data:
		print("Каталог данных пустой. Проверьте URL и повторите попытку.")
		return

	try:
		# Поиск введенной категории в общем каталоге
		category = search_category_in_catalog(url=url, catalog_list=catalog_data)
		if category is None:
			print("Категория не найдена. Проверьте URL и повторите попытку.")
			return

		data_list = []
		tasks = []
		total_count = get_total_count(page=1, shard=category['shard'], query=category['query'], low_price=low_price,
									  top_price=top_price, discount=discount)
		for page in range(1, (total_count // 100) + 2):
			tasks.append(
				asyncio.create_task(
					scrap_page(
						page=page,
						shard=category['shard'],
						query=category['query'],
						low_price=low_price,
						top_price=top_price,
						discount=discount
					))
			)

		result_list = await asyncio.gather(*tasks)

		for data in result_list:
			json_data = get_data_from_json(data)
			if len(json_data) > 0:
				data_list.extend(json_data)

		print(f"Сбор данных завершен. Собрано: {len(data_list)} товаров.")
		# Сохранение найденных данных
		save_excel(data_list, f"{category['name']}_from_{low_price}_to_{top_price}")
		print(f"Ссылка для проверки: {url}?priceU={low_price * 100};{top_price * 100}&discount={discount}")
	except TypeError:
		print("Ошибка! Возможно неверно указан раздел. Удалите все доп фильтры с ссылки")
	except PermissionError:
		print("Ошибка! Вы забыли закрыть созданный ранее excel файл. Закройте и повторите попытку")


async def main():
	url = "https://www.wildberries.ru/catalog/detyam/odezhda/dlya-devochek/bryuki-i-shorty"  # Ссылка на категорию
	low_price = 100
	top_price = 1_000_000
	discount = 10
	start = datetime.datetime.now()

	await parser(url=url, low_price=low_price, top_price=top_price, discount=discount)

	end = datetime.datetime.now()
	total = end - start
	print(f"Затраченное время на парсинг: {total}")


if __name__ == '__main__':
	asyncio.run(main())
