# 3.14.8, digest с Docker Hub на 05.10.2026; меняешь — сверь `pip freeze`.
# apt-слоёв нет: git был нужен для VCS-пина opentele, libglib2.0 — для PyQt5;
# opentele-ng ставится с PyPI без Qt, все зависимости — готовые колёса (pyaes — sdist
# на чистом Python, компилятор не нужен).
FROM python:3.14.8-slim@sha256:c3e521df8b2b498a7a682e7e18676771cb80c6b75b8699af886b2d554ce40151 AS builder

WORKDIR /app

COPY requirements.txt .

# ❗ Устанавливаем напрямую в /usr/local — БЕЗ --prefix
RUN pip install --no-cache-dir -r requirements.txt


FROM python:3.14.8-slim@sha256:c3e521df8b2b498a7a682e7e18676771cb80c6b75b8699af886b2d554ce40151

ENV PYTHONUNBUFFERED=1

WORKDIR /app

# ❗ Копируем зависимости из /usr/local
COPY --from=builder /usr/local /usr/local

# Копируем сам код
COPY ./app /app

CMD ["python", "handler.py"]
