#!/usr/bin/env python
import asyncio, logging, os, hashlib, argparse
from telethon.sessions import StringSession
from opentele.td import TDesktop
from opentele.api import API, UseCurrentSession
from dotenv import set_key
from opentele.exception import TFileNotFound

from bundle import build_telethon_client_from_bundle

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger()
# Снижаем уровень логов Telethon, чтобы скрыть информационные сообщения вроде "User is already connected!"
logging.getLogger("telethon").setLevel(logging.WARNING)

TELEGRAM_SESSION_ENV_KEY = "TELEGRAM_SESSION"


class MyTelegramClient:
    def __init__(self, tdata_name):
        self.tdata_name = tdata_name
        self.client = None
        self.me = None

    async def authorize_from_tdata(self):
        tdata_path = "tdatas/tdata/"
        if not os.path.exists(tdata_path):
            logger.error("Путь tdata не найден: %s", tdata_path)
            return False

        try:
            logger.info("Чтение tdata из %s", tdata_path)
            tdesk = TDesktop(tdata_path)
            if not tdesk.accounts:
                logger.error("Аккаунты не найдены в tdata")
                return False
        except TFileNotFound as e:
            logger.error("TFileNotFound: %s", e)
            return False

        session_hash = hashlib.md5("no_proxy".encode()).hexdigest()
        session_file = f"sessions/{self.tdata_name}_{session_hash}.session"

        try:
            logger.info("Создание сессии из tdata: %s", session_file)
            self.client = await tdesk.ToTelethon(
                session_file,
                UseCurrentSession,
                api=API.TelegramIOS.Generate(),
                auto_reconnect=True
            )
            await self.client.connect()
            self.me = await self.client.get_me()

            string_session = StringSession.save(self.client.session)
            set_key(".env", TELEGRAM_SESSION_ENV_KEY, string_session)

            os.remove(session_file)
            logger.info("Сессия успешно сохранена в .env")
            return True

        except Exception as e:
            logger.error("Ошибка получения сессии через tdata: %s", e)
            return False


async def authorize_from_bundle(json_path: str) -> bool:
    try:
        client, cfg = build_telethon_client_from_bundle(json_path)
        async with client:
            if not await client.is_user_authorized():
                logger.error("Сессия недействительна или отозвана для бандла: %s", json_path)
                return False
            me = await client.get_me()
            string_session = StringSession.save(client.session)
            set_key(".env", TELEGRAM_SESSION_ENV_KEY, string_session)
            logger.info("Сессия из бандла сохранена в .env. Пользователь: %s", me.id)
            return True
    except Exception as e:
        logger.error("Ошибка авторизации из бандла %s: %s", json_path, e)
        return False


async def main():
    parser = argparse.ArgumentParser(description="TData/Bundle авторизация и экспорт строки сессии в .env")
    parser.add_argument("--bundle", "-b", dest="bundle_json", help="Путь к JSON бандла (+ .session рядом)")
    args = parser.parse_args()

    bundle_json = args.bundle_json or os.environ.get("BUNDLE_JSON_PATH")
    if bundle_json:
        if not os.path.exists(bundle_json):
            logger.error("Файл бандла не найден: %s", bundle_json)
            return
        logger.info("Режим: авторизация из бандла JSON: %s", bundle_json)
        ok = await authorize_from_bundle(bundle_json)
        if not ok:
            logger.error("Авторизация из бандла не удалась")
        return

    logger.info("Режим: авторизация из tdata")
    client = MyTelegramClient("example_tdata")
    if not await client.authorize_from_tdata():
        logger.error("Авторизация не удалась")

if __name__ == "__main__":
    asyncio.run(main())
