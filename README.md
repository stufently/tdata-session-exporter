# TData Session Exporter

Небольшой инструмент для извлечения строки сессии Telegram из папки `tdata` (Telegram Desktop) и сохранения её в формате переменной окружения в файле `.env`.

## Возможности

- Берёт папку `tdata`, как её хранит Telegram Desktop (Windows, macOS, Linux)  
- Декодирует из неё MTProto‑ключи и идентификатор дата‑центра  
- Собирает корректную строку сессии  
- Сохраняет результат в файл `.env` с переменной `TELEGRAM_SESSION`

## Требования

- Python 3.8 или выше  
- Пакет `tdesktop` или аналог для чтения `tdata` (см. `requirements.txt`)

### Зависимости запинены (важно при правках)

Все строки в `requirements.txt` зафиксированы по версии, включая VCS-зависимость:
`opentele @ git+https://github.com/thedemons/opentele.git@1a6f0816…`. Раньше ref
у git-URL не было — pip тянул текущий `HEAD` чужого репозитория, т.е. в образ
попадал бы любой новый апстрим-коммит без нашего решения (supply-chain-риск).
`1a6f0816eac47ff3cb907af72ed9f8cbbbe8fba0` — это HEAD ветки `main` на 2026-07-25
(апстрим не обновлялся с 2024-07-15), то есть ровно то, что ставилось раньше;
тегов у апстрима нет, поэтому пин только по SHA. Обновление зависимости = явная
смена SHA в `requirements.txt` + пересборка образа.

Экшены в `.github/workflows/ci.yml` тоже запинены по commit-SHA: джоба билдит и
пушит `ghcr.io/stufently/tdata-session-exporter:latest`, т.е. любой пуш в `main`
ПЕРЕЗАЛИВАЕТ образ под тем же тегом. Правки, не требующие релиза образа, пуши с
`[skip ci]` в сообщении коммита.

По той же причине `docker-compose.yml` тянет образ не по голому `:latest`, а по
дайджесту (`:latest@sha256:2c974906…` — то, на что тег указывал на момент пина).
После осознанного релиза образа дайджест в compose нужно обновить вручную.

## Установка

```bash
git clone https://github.com/stufently/tdata-session-exporter.git
cd tdata-session-exporter
python -m venv venv
source venv/bin/activate       # Linux/macOS
venv\Scripts\activate.bat      # Windows
pip install --upgrade pip
pip install -r requirements.txt
```

## Как использовать

### Вариант A. Авто-режим (просто положить tdata и запустить)

1) Положите папку `tdata` в один из путей:
   - `accounts/<ИМЯ_АККАУНТА>/tdata` (рекомендуется)
   - `./tdata`
2) Запустите:
```bash
python app/handler.py
```
3) В корне проекта появятся файлы:
   - `<ИМЯ_АККАУНТА>.json`
   - `<ИМЯ_АККАУНТА>.session`

Где `<ИМЯ_АККАУНТА>` — это имя папки над `tdata` (например, `+2349049675164`).

### Вариант B. Явно указать путь и имя

```bash
python app/handler.py \
  --export-tdata "/абс/путь/до/.../tdata" \
  --export-out   "." \
  --export-basename "+2349049675164"
```

### Вариант C. Авторизация из бандла (JSON+.session)

```bash
python app/handler.py --bundle "/abs/path/accounts/+2349049675164.json"
```
При успехе строка сессии будет записана в `.env` (`TELEGRAM_SESSION`).

## 🐳 Docker Deployment

Run the service with Docker Compose:

```bash
docker-compose up -d
```
To update to a new image version:
```bash
docker-compose pull
docker-compose down
docker-compose up -d
```
