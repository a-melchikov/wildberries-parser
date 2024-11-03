# telegram_bot/Dockerfile
FROM python:3.12-slim

RUN pip install poetry

WORKDIR /bot

COPY pyproject.toml poetry.lock ./

RUN poetry config virtualenvs.create false && poetry install --only telegram --no-interaction --no-ansi

COPY . .

ENV PYTHONPATH=/bot

CMD ["python", "app.py"]
