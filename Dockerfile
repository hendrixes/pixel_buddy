FROM python:3.13-slim-trixie

COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /bin/

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    UV_NO_DEV=1

WORKDIR /app

RUN apt-get update \
    && apt-get install -y --no-install-recommends fonts-dejavu-core \
    && rm -rf /var/lib/apt/lists/*

COPY pyproject.toml uv.lock ./
RUN uv sync --locked --no-dev

COPY . .
RUN mkdir -p instance

EXPOSE 5000

CMD ["sh", "-c", "uv run python init_db.py && uv run flask --app app.main run --host=0.0.0.0 --port=5000"]
