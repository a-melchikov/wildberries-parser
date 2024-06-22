from catalog_fetcher import CatalogFetcher
from main import CATALOG_URL, PROXIES

cf = CatalogFetcher(CATALOG_URL, PROXIES)
with open("urls.txt", "w", encoding="utf-8") as file:
    for cat in cf.get_data_category(cf.get_catalogs_wb()):
        if "zhenshchinam" in cat["url"] or "detyam" in cat["url"]:
            file.write(f'https://www.wildberries.ru{cat["url"]}\n')

urls: list[str] = []
with open("urls.txt", "r", encoding="utf-8") as file:
    for row in file:
        urls.append(row.strip())
print(urls)
