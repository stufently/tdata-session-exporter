FROM python:3.12.9-slim AS builder

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    git \
    gcc \
    build-essential \
    python3-dev \
    libglib2.0-0 \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .

# ❗ Устанавливаем напрямую в /usr/local — БЕЗ --prefix
RUN pip install --no-cache-dir -r requirements.txt


FROM python:3.12.9-slim

ENV PYTHONUNBUFFERED=1

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    libglib2.0-0 \
    && rm -rf /var/lib/apt/lists/*

# ❗ Копируем зависимости из /usr/local
COPY --from=builder /usr/local /usr/local

# Копируем сам код
COPY ./app /app

CMD ["python", "handler.py"]
