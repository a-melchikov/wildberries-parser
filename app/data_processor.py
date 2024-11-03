import asyncio
import os
from logging import Logger, getLogger
from typing import Any, Literal
from math import ceil

import shutil
import pandas as pd
from dotenv import load_dotenv

from notification import NotificationService

load_dotenv()
logger: Logger = getLogger(__name__)


class DataProcessor:
    def __init__(self, current_dir: str, previous_dir: str, changes_dir: str) -> None:
        self.current_dir: str = os.path.abspath(current_dir)
        self.previous_dir: str = os.path.abspath(previous_dir)
        self.changes_dir: str = os.path.abspath(changes_dir)

        for directory in [self.current_dir, self.previous_dir, self.changes_dir]:
            os.makedirs(directory, exist_ok=True)
            logger.info("Каталог %s создан или уже существует", directory)

    @staticmethod
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

    def save_csv(self, data: list, filename: str) -> None:
        """Сохраняем данные в CSV"""
        df = pd.DataFrame(data)
        file_path: str = os.path.join(self.current_dir, f"{filename}.csv")
        df.to_csv(file_path, index=False)

    def move_data_to_previous(self) -> None:
        """Перемещение данных из current_data в previous_data"""
        if os.path.exists(self.current_dir):
            if not os.path.exists(self.previous_dir):
                os.makedirs(self.previous_dir)
            for filename in os.listdir(self.current_dir):
                shutil.move(
                    os.path.join(self.current_dir, filename),
                    os.path.join(self.previous_dir, filename),
                )
            logger.info("Данные перемещены в %s", self.previous_dir)
        else:
            logger.warning("Каталог %s не существует", self.current_dir)

    @staticmethod
    def beautify_number(number: int) -> str:
        """Преобразует число в красивый вид"""
        fancy_digits = "𝟬𝟭𝟮𝟯𝟰𝟱𝟲𝟳𝟴𝟵"
        return "".join(fancy_digits[x] for x in list(map(int, str(number))))

    @staticmethod
    def calculate_percent_change(
        current_price: float, previous_price: float
    ) -> float | Any | Literal[0]:
        """Вычисляет процентное изменение между двумя ценами"""
        if previous_price == 0:
            return float("inf") if current_price != 0 else 0
        return ((current_price - previous_price) / previous_price) * 100

    async def compare_and_save_changes(
        self,
        token: str,
        channel_ids: list[str],
        price_difference_percentage: int | float,
    ) -> None:
        """Сравнивает файлы и сохраняет изменения."""
        logger.info("Начало процесса сравнения и сохранения изменений")

        if not os.path.exists(self.changes_dir):
            os.makedirs(self.changes_dir)
            logger.info("Создан каталог для изменений: %s", self.changes_dir)

        columns_to_include: list[str] = [
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

        for current_file in os.listdir(self.current_dir):
            current_filepath = os.path.join(self.current_dir, current_file)
            previous_filepath = os.path.join(self.previous_dir, current_file)

            if os.path.exists(previous_filepath):
                logger.info("Обработка файла: %s", current_file)
                current_df: pd.DataFrame = pd.read_csv(current_filepath)
                previous_df: pd.DataFrame = pd.read_csv(previous_filepath)

                changes_df = await self.process_file(
                    current_df,
                    previous_df,
                    columns_to_include,
                    price_difference_percentage,
                )

                if not changes_df.empty:
                    await self.handle_changes(
                        changes_df, current_file, token, channel_ids
                    )
                else:
                    logger.info("Изменений не найдено для файла %s", current_file)
            else:
                logger.warning("Предыдущий файл для %s не найден", current_file)

        logger.info("Процесс сравнения и сохранения изменений завершён")

    async def process_file(
        self,
        current_df: pd.DataFrame,
        previous_df: pd.DataFrame,
        columns_to_include: list[str],
        price_difference_percentage: int | float,
    ) -> pd.DataFrame:
        """Обрабатывает один файл и возвращает изменения."""
        merged_df: pd.DataFrame = current_df.merge(
            previous_df, on="id", suffixes=("_current", "_previous")
        )
        merged_df["percent_change"] = merged_df.apply(
            lambda row: self.calculate_percent_change(
                row["salePriceU_current"], row["salePriceU_previous"]
            ),
            axis=1,
        )

        return merged_df[merged_df["percent_change"] < -price_difference_percentage][
            columns_to_include
        ]

    async def handle_changes(
        self,
        changes_df: pd.DataFrame,
        current_file: str,
        token: str,
        channel_ids: list[str],
    ) -> None:
        """Обрабатывает изменения и сохраняет их."""
        changes_filepath = os.path.join(self.changes_dir, f"changes_{current_file}")
        changes_df.columns = [col.replace("_current", "") for col in changes_df.columns]
        changes_df.to_csv(changes_filepath, index=False)
        logger.info("Изменения сохранены в %s", changes_filepath)

        notification_service = NotificationService(token, channel_ids)
        await self.send_notifications(changes_df, notification_service)

    async def send_notifications(
        self, changes_df: pd.DataFrame, notification_service: NotificationService
    ) -> None:
        """Отправляет уведомления о каждом изменении."""
        tasks = [
            self.send_notification(row, notification_service)
            for _, row in changes_df.iterrows()
        ]
        await asyncio.gather(*tasks)

    async def send_notification(
        self, row: pd.Series, notification_service: NotificationService
    ) -> None:
        """Отправляет уведомление об одном изменении."""
        discount_percent = ceil(
            -self.calculate_percent_change(
                row["salePriceU"], row["salePriceU_previous"]
            )
        )
        message: str = (
            f"📢 <b>{str(row['name']).upper()}</b>\n\n"
            f"🔻 <b>Цена была:</b> <code>{row['salePriceU_previous']}₽</code>\n"
            f"🔺 <b>Цена стала:</b> <code>{row['salePriceU']}₽</code>\n\n"
            f"💬 <b>Количество отзывов:</b> <code>{row['feedbacks']}</code>\n"
            f"⭐️ <b>Рейтинг:</b> <code>{row['supplierRating']}</code>\n\n"
            f"📉 <b>Цена уменьшилась на:</b> <code>{self.beautify_number(discount_percent)}%</code>\n\n"
            f"🔗 <a href='{row['link']}'>Ссылка на товар</a>"
        )
        await notification_service.send_message(message)


async def main():
    data_processor = DataProcessor(
        current_dir="current_data",
        previous_dir="previous_data",
        changes_dir="../changes_data",
    )
    await data_processor.compare_and_save_changes(
        os.getenv("token"), os.getenv("channel_id").split(","), 30
    )


if __name__ == "__main__":
    asyncio.run(main())
