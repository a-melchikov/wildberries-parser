from logging import Logger, getLogger
import requests

logger: Logger = getLogger(__name__)


class NotificationService:
    def __init__(self, token: str, channel_ids: list[str]) -> None:
        self.token: str = token
        self.channel_ids: list[str] = channel_ids
        self.url: str = f"https://api.telegram.org/bot{self.token}/sendMessage"

    def send_message(self, text: str) -> None:
        for channel_id in self.channel_ids:
            r = requests.post(
                self.url,
                data={"chat_id": channel_id, "text": text, "parse_mode": "HTML"},
            )
