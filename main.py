import requests

HEADERS: dict[str, str] = {
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


url: str = "https://catalog.wb.ru/catalog/children_girls1/v2/catalog?appType=1&cat=8310&curr=rub&dest=-1257786&sort=popular&spp=30"

r = requests.get(url, headers=HEADERS)
print(r.json())
