import logging
import pytest

from app.logging_config import LogConfig, LoggerSetup, LogLevel


@pytest.fixture
def log_config():
    """Фикстура для конфигурации логирования с уровнем DEBUG."""
    return LogConfig(
        level=LogLevel.DEBUG,  # Устанавливаем уровень DEBUG
        filename=None,  # Не будем создавать файл для тестов
        console_level=LogLevel.INFO,
        file_level=LogLevel.WARNING,
    )


@pytest.fixture
def logger_setup(log_config):
    """Фикстура для создания экземпляра LoggerSetup с тестовой конфигурацией."""
    return LoggerSetup(log_config=log_config)


def test_logger_creation(logger_setup):
    """Тестирует создание экземпляра Logger с заданным именем и уровнем."""
    logger = logger_setup.get_logger()
    assert isinstance(logger, logging.Logger)
    assert logger.level == LogLevel.DEBUG.value


def test_get_handlers(logger_setup):
    """Тестирует наличие обработчиков логирования."""
    handlers = logger_setup._get_handlers()  # pylint: disable=W0212

    assert (
        len(handlers) == 1
    )  # Должен быть только консольный обработчик, так как filename=None
    assert isinstance(handlers[0], logging.StreamHandler)


def test_console_handler_level(logger_setup):
    """Проверяет уровень консольного обработчика."""
    handlers = logger_setup._get_handlers()  # pylint: disable=W0212
    console_handler = handlers[0]
    assert console_handler.level == LogLevel.INFO.value  # Сравниваем с value


def test_logging_message(logger_setup, caplog):
    """Проверяет, что сообщение логируется на нужном уровне."""
    logger = logger_setup.get_logger()  # pylint: disable=W0212
    with caplog.at_level(logging.INFO):  # Устанавливаем уровень логирования для caplog
        logger.info("This is a test info message.")
        logger.error("This is a test error message.")

    assert "This is a test info message." in caplog.text
    assert (
        "This is a test error message." in caplog.text
    )  # Проверка сообщения об ошибке
