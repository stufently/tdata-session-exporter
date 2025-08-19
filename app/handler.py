#!/usr/bin/env python
import asyncio, logging, os, hashlib, argparse, json, time, shutil, platform, locale, random, string
from typing import Optional
from telethon.sessions import StringSession
from opentele.td import TDesktop
from opentele.api import API, UseCurrentSession
from dotenv import set_key
from opentele.exception import TFileNotFound
from telethon import functions

# Поддержка бандлов через отдельный модуль была убрана в текущей версии.

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


def _derive_basename_from_tdata(tdata_path: str) -> str:
    base = os.path.basename(os.path.normpath(tdata_path))
    if base.lower() == 'tdata':
        return os.path.basename(os.path.dirname(os.path.normpath(tdata_path))) or 'account'
    return base or 'account'


def _find_single_tdata() -> Optional[str]:
    def _is_valid_tdata(p: str) -> bool:
        try:
            _ensure_compat_tdata(p)
            td = TDesktop(p)
            return bool(td.accounts)
        except Exception:
            return False

    candidates = []
    # По стандартным путям
    paths_to_check = [
        os.environ.get('SIMPLE_TDATA_PATH'),
        os.path.join('accounts'),
        os.path.join('tdatas', 'tdata'),
        'tdata',
    ]
    # accounts/*/tdata
    acc_dir = os.path.join('accounts')
    if os.path.isdir(acc_dir):
        for name in os.listdir(acc_dir):
            p = os.path.join(acc_dir, name, 'tdata')
            if os.path.isdir(p):
                candidates.append(p)
    # добавляем прямые пути
    for p in paths_to_check:
        if not p:
            continue
        if os.path.isdir(p) and os.path.basename(os.path.normpath(p)).lower() == 'tdata':
            candidates.append(p)
    # Уникализируем
    uniq = []
    seen = set()
    for p in candidates:
        ap = os.path.abspath(p)
        if ap not in seen:
            seen.add(ap)
            uniq.append(ap)
    # Валидируем кандидатов через попытку чтения аккаунтов
    valid = [p for p in uniq if _is_valid_tdata(p)]
    if len(valid) == 1:
        return valid[0]
    # Если несколько валидных — попробуем предпочесть из accounts/*/tdata
    valid_accounts = [p for p in valid if os.path.basename(os.path.dirname(p))]
    if len(valid_accounts) == 1:
        return valid_accounts[0]
    return None


def _ensure_compat_tdata(tdata_path: str) -> None:
    """Готовит tdata к чтению: создает совместимые имена через symlink/копию.
    Ничего не делает, если уже всё в норме. Безопасно вызывать многократно.
    """
    try:
        # Файлы: key_data vs key_datas, map vs maps
        pairs = [
            (os.path.join(tdata_path, 'key_data'), os.path.join(tdata_path, 'key_datas')),
            (os.path.join(tdata_path, 'map'), os.path.join(tdata_path, 'maps')),
        ]
        for expected, alt in pairs:
            if not os.path.exists(expected) and os.path.exists(alt):
                # Пытаемся создать symlink; если не получилось — копируем файл
                try:
                    os.symlink(alt, expected)
                except Exception:
                    try:
                        if os.path.isfile(alt):
                            shutil.copyfile(alt, expected)
                    except Exception:
                        pass

        # Директория каталога базы: D877F783D5D3EF8C vs D877F783D5D3EF8Cs
        expected_dir = os.path.join(tdata_path, 'D877F783D5D3EF8C')
        alt_dir = os.path.join(tdata_path, 'D877F783D5D3EF8Cs')
        if (not os.path.exists(expected_dir)) and os.path.isdir(alt_dir):
            try:
                os.symlink(alt_dir, expected_dir)
            except Exception:
                pass
    except Exception:
        # Не мешаем основному потоку при любой ошибке вспомогательной подготовки
        pass


def _generate_device_meta(seed_key: str) -> dict:
    """Генерирует реалистичные метаданные устройства в стиле продаваемых бандлов.
    Детеминированно по seed_key (например, basename), чтобы значения были стабильными.
    """
    rnd = random.Random(hashlib.md5(seed_key.encode('utf-8')).hexdigest())

    # device: 7-10 заглавных букв/цифр + суффикс
    length = rnd.randint(7, 10)
    dev_core = ''.join(rnd.choice(string.ascii_uppercase + string.digits) for _ in range(length))
    device = f"{dev_core}-EXTREME"

    system = platform.system()
    release = platform.release()
    arch = platform.machine()

    if system.lower().startswith('win'):
        sdk = f"Windows {release if release else '10'}"
        app_version = "6.0.2 x64" if '64' in arch or arch.endswith('64') else "6.0.2"
    elif system.lower() == 'darwin':
        sdk = "macOS"
        app_version = "6.0.2 x64"
    else:
        sdk = f"Linux {release}" if release else "Linux"
        app_version = "6.0.2 x64"

    # Языки
    try:
        loc = locale.getdefaultlocale()
        sys_code = (loc[0] or 'en').split('_')[0]
    except Exception:
        sys_code = 'en'

    return {
        "device": device,
        "sdk": sdk,
        "app_version": app_version,
        "system_lang_pack": sys_code,
        "system_lang_code": sys_code,
        "lang_pack": "tdesktop",
        "lang_code": sys_code,
    }


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
            # Пытаемся получить реальные данные устройства из текущей авторизации
            current_device = None
            try:
                auths = await client(functions.account.GetAuthorizationsRequest())
                if getattr(auths, 'authorizations', None):
                    for a in auths.authorizations:
                        if getattr(a, 'current', False):
                            current_device = a
                            break
            except Exception:
                current_device = None

        # Собираем JSON в "продаваемом" формате
        # Предпочитаем реальные значения из текущей авторизации, иначе — генерация/ENV
        meta = _generate_device_meta(basename)
        real_device = None
        real_sdk = None
        real_app_version = None
        if current_device:
            # device_model, platform, system_version, app_name, app_version
            try:
                if getattr(current_device, 'device_model', None):
                    real_device = current_device.device_model
                sv = getattr(current_device, 'system_version', None) or ''
                pf = getattr(current_device, 'platform', None) or ''
                real_sdk = (pf + ' ' + sv).strip() or None
                av = getattr(current_device, 'app_version', None)
                real_app_version = av if av else None
            except Exception:
                pass

        device = os.environ.get("BUNDLE_DEVICE", real_device or meta["device"])
        sdk = os.environ.get("BUNDLE_SDK", real_sdk or meta["sdk"])
        app_version = os.environ.get("BUNDLE_APP_VERSION", real_app_version or meta["app_version"])
        system_lang_pack = os.environ.get("BUNDLE_SYS_LANG_PACK", meta["system_lang_pack"])
        system_lang_code = os.environ.get("BUNDLE_SYS_LANG_CODE", meta["system_lang_code"])
        lang_pack = os.environ.get("BUNDLE_LANG_PACK", meta["lang_pack"])
        lang_code = os.environ.get("BUNDLE_LANG_CODE", meta["lang_code"])

        cfg = {
            "app_id": int(CustomAPI.api_id),
            "app_hash": str(CustomAPI.api_hash),
            "device": device,
            "sdk": sdk,
            "app_version": app_version,
            "system_lang_pack": system_lang_pack,
            "system_lang_code": system_lang_code,
            "lang_pack": lang_pack,
            "lang_code": lang_code,
            "twoFA": None,
            "role": "",
            "id": getattr(me, 'id', None) if me else None,
            "phone": getattr(me, 'phone', None) if me else None,
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
    parser = argparse.ArgumentParser(description="TData экспорт/авторизация")
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

    # Если аргументов нет — пытаемся простой экспорт:
    auto_tdata = _find_single_tdata()
    if auto_tdata:
        basename = _derive_basename_from_tdata(auto_tdata)
        logger.info("Обнаружен tdata: %s", auto_tdata)
        ok = await export_bundle_from_tdata(
            tdata_path=auto_tdata,
            out_dir=os.getcwd(),
            basename=basename,
        )
        if not ok:
            logger.error("Авто-экспорт бандла из tdata не удался")
        return

    logger.info("Режим: авторизация из tdata (стандартный путь)")
    client = MyTelegramClient("example_tdata")
    if not await client.authorize_from_tdata():
        logger.error("Авторизация не удалась")

if __name__ == "__main__":
    asyncio.run(main())
