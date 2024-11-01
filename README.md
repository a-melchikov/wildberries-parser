# Wildberries Parser с Интеграцией в Telegram

Этот проект представляет собой парсер для получения данных с Wildberries, с интеграцией в Telegram для отправки уведомлений.

## Требования

- Python 3.12+
- Установленные зависимости из pyproject.toml

## Установка

1. Склонируйте репозиторий:

```bash
git clone https://github.com/a-melchikov/wildberries-parser.git
cd wildberries-parser
```

2. Установите зависимости с помощью Poetry:

```bash
poetry install
```

3. Настройте файл .env (пример структуры ниже).
4. Установите pre-commit хуки:

```bash
poetry run pre-commit install
```

## Структура .env файла

```env
proxy=http://username:password@ip:port
channel_id=user_id,user_id,user_id...
token=TELEGRAM_BOT_TOKEN
```

## Используемые Инструменты

- black
- pylint
- pytest

## Запуск проекта

```bash
poetry run python main.py
```

## Дополнительно

### Проверка хуков перед коммитом

Чтобы проверить работу всех хуков вручную, выполните команду:

```bash
poetry run pre-commit run --all-files
```
