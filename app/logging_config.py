from dataclasses import dataclass
from enum import Enum
import logging
from logging import (
    Handler,
    Logger,
    getLogger,
    basicConfig,
    FileHandler,
    StreamHandler,
)
from typing import List, Optional


class LogLevel(Enum):
    DEBUG = logging.DEBUG
    INFO = logging.INFO
    WARNING = logging.WARNING
    ERROR = logging.ERROR
    CRITICAL = logging.CRITICAL


@dataclass
class LogConfig:
    """
    Дата-класс отвечающий за конфигурацию логирования.

    :param level: Уровень логирования.
    :param filename: Имя файла для записи логов. Если None, логирование в файл отключено.
    :param console_level: Уровень логирования для консоли.
    :param file_level: Уровень логирования для файла.
    """

    level: LogLevel = LogLevel.INFO
    filename: Optional[str] = "data.log"
    console_level: LogLevel = LogLevel.INFO
    file_level: LogLevel = LogLevel.INFO


class LoggerSetup:
    """
    Класс для настройки и конфигурирования логирования.
    """

    def __init__(
        self,
        logger_name: str = __name__,
        log_config: LogConfig = LogConfig(level=LogLevel.DEBUG),
    ) -> None:
        self.logger: Logger = getLogger(logger_name)
        self._log_config: LogConfig = log_config
        self._setup_logger()

    def _setup_logger(self) -> None:
        """
        Настраивает логгер с файловыми и консольными обработчиками.
        """
        FORMAT = "%(asctime)s : %(name)s : %(levelname)s : %(message)s"
        try:
            handlers: List[logging.Handler] = self._get_handlers()
            basicConfig(
                level=self._log_config.level.value,
                format=FORMAT,
                handlers=handlers,
            )
        except Exception as e:
            self.logger.error("Ошибка при настройке логгера: %s", e)

    def _get_handlers(self) -> List[Handler]:
        """
        Создает список обработчиков логирования.

        :return: Список обработчиков логирования.
        """
        handlers: List[Handler] = []

        if self._log_config.filename:
            file_handler = FileHandler(self._log_config.filename)
            file_handler.setLevel(self._log_config.file_level.value)
            handlers.append(file_handler)

        console = StreamHandler()
        console.setLevel(self._log_config.console_level.value)
        handlers.append(console)

        return handlers

    def get_logger(self) -> Logger:
        """
        Возвращает настроенный логгер.

        :return: Экземпляр настроенного логгера.
        """
        return self.logger


__all__ = ["LogConfig", "LoggerSetup", "LogLevel"]

if __name__ == "__main__":
    log_config = LogConfig(
        level=LogLevel.INFO,
        filename="app.log",
        console_level=LogLevel.DEBUG,
        file_level=LogLevel.WARNING,
    )
    logger_setup = LoggerSetup(log_config=log_config)
    logger: Logger = logger_setup.get_logger()
    logger.info("Сообщение уровня INFO")
    logger.error("Сообщение уровня ERROR")
