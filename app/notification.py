import os
from logging import Logger, getLogger
import asyncio
from dotenv import load_dotenv
import aiohttp

load_dotenv()

logger: Logger = getLogger(__name__)


class NotificationService:
    def __init__(self, token: str, channel_ids: list[str]) -> None:
        self.token: str = token
        self.channel_ids: list[str] = channel_ids
        self.url: str = f"https://api.telegram.org/bot{self.token}/sendMessage"

    async def send_message(self, text: str) -> None:
        async with aiohttp.ClientSession() as session:
            tasks = []
            for channel_id in self.channel_ids:
                payload: dict[str, str] = {
                    "chat_id": channel_id,
                    "text": text,
                    "parse_mode": "HTML",
                }
                tasks.append(session.post(self.url, data=payload))

            responses = await asyncio.gather(*tasks)
            for response in responses:
                if response.status != 200:
                    logger.error("Ошибка при отправке сообщения: %s", response.status)


async def main():
    notification_service = NotificationService(
        os.getenv("token"), os.getenv("channel_id").split(",")
    )
    tasks = []
    message = "hello" * 5
    tasks.append(notification_service.send_message(message))
    await asyncio.gather(*tasks)


if __name__ == "__main__":
    asyncio.run(main())
