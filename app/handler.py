#!/usr/bin/env python
import asyncio, logging, os, hashlib, argparse, json, time
from typing import Optional
from telethon.sessions import StringSession
from opentele.td import TDesktop
from opentele.api import API, UseCurrentSession
from dotenv import set_key
from opentele.exception import TFileNotFound

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger()

TELEGRAM_SESSION_ENV_KEY = "TELEGRAM_SESSION"

class MyTelegramClient:
    def __init__(self, tdata_name):
        self.tdata_name = tdata_name
        self.client = None
        self.me = None

    async def authorize(self):
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


async def export_bundle_from_tdata(tdata_path: str, out_dir: str, basename: str,
                                   api_id: Optional[int] = None, api_hash: Optional[str] = None) -> bool:
    if not os.path.isdir(tdata_path):
        logger.error("Директория tdata не найдена: %s", tdata_path)
        return False

    os.makedirs(out_dir, exist_ok=True)

    try:
        logger.info("Чтение tdata из %s", tdata_path)
        tdesk = TDesktop(tdata_path)
        if not tdesk.accounts:
            logger.error("Аккаунты не найдены в tdata")
            return False
    except TFileNotFound as e:
        logger.error("TFileNotFound: %s", e)
        return False

    session_path = os.path.join(out_dir, f"{basename}.session")
    json_path = os.path.join(out_dir, f"{basename}.json")

    # Подготавливаем API класс для opentele (ожидается класс, а не инстанс)
    if not api_id or not api_hash:
        api_id = 2040
        api_hash = "b18441a1ff607e10a989891a5462e627"
    CustomAPI = type(
        "CustomAPI",
        (API,),
        {
            "api_id": int(api_id),
            "api_hash": str(api_hash),
        },
    )

    try:
        logger.info("Генерация Telethon .session из tdata: %s", session_path)
        client = await tdesk.ToTelethon(
            session_path,
            UseCurrentSession,
            api=CustomAPI,
            auto_reconnect=False
        )
        async with client:
            me = await client.get_me()

        # Собираем JSON (минимально необходимое + базовые метаданные)
        cfg = {
            "app_id": int(CustomAPI.api_id),
            "app_hash": str(CustomAPI.api_hash),
            "device": "tdata-export",
            "sdk": "unknown",
            "app_version": "unknown",
            "system_lang_pack": "en",
            "system_lang_code": "en",
            "lang_pack": "tdesktop",
            "lang_code": "en",
            "twoFA": None,
            "role": "",
            "id": getattr(me, 'id', None) if me else None,
            "phone": None,
            "username": getattr(me, 'username', None) if me else None,
            "date_of_birth": None,
            "date_of_birth_integrity": None,
            "is_premium": bool(getattr(me, 'premium', False)) if me else False,
            "has_profile_pic": bool(getattr(me, 'photo', None)) if me else False,
            "spamblock": None,
            "register_time": None,
            "last_check_time": int(time.time()),
            "avatar": None,
            "first_name": getattr(me, 'first_name', "") if me else "",
            "last_name": getattr(me, 'last_name', "") if me else "",
            "sex": None,
            "proxy": None,
            "ipv6": False,
            "session_file": basename
        }
        with open(json_path, "w", encoding="utf-8") as f:
            json.dump(cfg, f, ensure_ascii=False)

        logger.info("Бандл сохранён: %s и %s", json_path, session_path)
        return True
    except Exception as e:
        logger.error("Ошибка экспорта бандла из tdata: %s", e)
        # При ошибке не удаляем возможный .session, чтобы можно было проанализировать
        return False


async def main():
    parser = argparse.ArgumentParser(description="TData/Bundle авторизация и экспорт")
    parser.add_argument("--bundle", "-b", dest="bundle_json", help="Путь к JSON бандла (+ .session рядом)")
    # Экспорт бандла из tdata
    parser.add_argument("--export-tdata", dest="export_tdata", help="Путь к директории tdata для экспорта бандла")
    parser.add_argument("--export-out", dest="export_out", help="Директория для сохранения бандла")
    parser.add_argument("--export-basename", dest="export_basename", help="Базовое имя для файлов бандла (без расширения)")
    parser.add_argument("--export-api-id", dest="export_api_id", type=int, help="API_ID для бандла (необязательно)")
    parser.add_argument("--export-api-hash", dest="export_api_hash", help="API_HASH для бандла (необязательно)")
    args = parser.parse_args()

    # Режим экспорта бандла из tdata
    if args.export_tdata and args.export_out and args.export_basename:
        ok = await export_bundle_from_tdata(
            tdata_path=args.export_tdata,
            out_dir=args.export_out,
            basename=args.export_basename,
            api_id=args.export_api_id,
            api_hash=args.export_api_hash,
        )
        if not ok:
            logger.error("Экспорт бандла из tdata не удался")
        return

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
    if not await client.authorize():
        logger.error("Авторизация не удалась")

if __name__ == "__main__":
    asyncio.run(main())
