# app/Dockerfile
FROM python:3.12-slim

RUN pip install poetry

WORKDIR /app

COPY pyproject.toml poetry.lock ./

RUN poetry config virtualenvs.create false && poetry install --only main --no-interaction --no-ansi

COPY . .

ENV PYTHONPATH=/app

CMD ["python", "main.py"]
