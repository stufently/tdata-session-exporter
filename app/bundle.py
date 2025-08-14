import os, json
from typing import Optional, Tuple

from telethon import TelegramClient


def _build_proxy_from_config(proxy_cfg: Optional[dict]):
    if not proxy_cfg:
        return None
    try:
        import socks  # type: ignore
    except Exception:
        return None

    proxy_type_name = str(proxy_cfg.get("type", "")).lower()
    proxy_type_map = {
        "socks5": getattr(socks, "SOCKS5", None),
        "socks4": getattr(socks, "SOCKS4", None),
        "http": getattr(socks, "HTTP", None),
    }
    proxy_type = proxy_type_map.get(proxy_type_name)
    if not proxy_type:
        return None

    host = proxy_cfg.get("host")
    port = proxy_cfg.get("port")
    if not host or not port:
        return None

    username = proxy_cfg.get("username")
    password = proxy_cfg.get("password")

    # (proxy_type, addr, port, rdns, username, password)
    return (
        proxy_type,
        host,
        int(port),
        True,
        username,
        password,
    )


def load_bundle_config(json_path: str) -> Tuple[dict, str]:
    """
    Загружает JSON бандла и возвращает кортеж (config, session_path_no_ext).

    session_path_no_ext — абсолютный путь к файлу сессии БЕЗ расширения .session,
    чтобы Telethon корректно нашёл .session рядом с JSON.
    """
    with open(json_path, "r", encoding="utf-8") as f:
        cfg = json.load(f)

    # Поля совместимости: app_id/api_id и app_hash
    api_id = cfg.get("app_id") or cfg.get("api_id")
    api_hash = cfg.get("app_hash")
    if not api_id or not api_hash:
        raise ValueError("В JSON отсутствуют app_id/app_hash")

    # Имя сессии: явное поле или имя json-файла
    session_file = cfg.get("session_file")
    if not session_file:
        # берем имя JSON без расширения
        session_file = os.path.splitext(os.path.basename(json_path))[0]

    session_basename = os.path.splitext(session_file)[0]
    base_dir = os.path.dirname(os.path.abspath(json_path))
    session_path_no_ext = os.path.join(base_dir, session_basename)

    # Дополнительно кладём обратно (нормализованные) поля
    cfg["app_id"] = int(api_id)
    cfg["app_hash"] = str(api_hash)
    cfg["session_file"] = session_basename

    return cfg, session_path_no_ext


def build_telethon_client_from_bundle(json_path: str) -> Tuple[TelegramClient, dict]:
    """
    Собирает TelegramClient (Telethon) по бандлу JSON+.session и возвращает (client, cfg).
    Клиента НЕ подключаем здесь — это на усмотрение вызывающего кода.
    """
    cfg, session_path_no_ext = load_bundle_config(json_path)
    proxy = _build_proxy_from_config(cfg.get("proxy"))

    client = TelegramClient(
        session=session_path_no_ext,
        api_id=int(cfg["app_id"]),
        api_hash=str(cfg["app_hash"]),
        proxy=proxy,
    )
    return client, cfg


