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

```bash
Кладем папку с tdata в корень проекта, с помощью скрипта извлекаем сессию.
Далее полученную переменную в файле .env с переменной TELEGRAM_SESSION вставляем в проект, где есть есть возможность подключения по СЕССИИ, а не по tdata
```

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
