# Веха: бамп зависимостей и Python 3.14 в tdata-session-exporter

- **Репозиторий:** `git@github.com:stufently/tdata-session-exporter.git`, ветка по умолчанию `main`.
- **Дата постановки:** 23.09.2026.
- **Базовый коммит:** `af5598da190559c5deee7fe646e78cc0d89cee7e` «Point proxy sample at zp2.8qw.ru».
- **Исполнитель:** `gk` (Grok). Веха механическая (пины, базовый образ), её
  проверяют сборка и импорт в Docker. Приёмку и ревью диффа делает постановщик.

## Где работать

Клон `/home/deploy/gitlab/9qw/tg-claude-userbot/tmp/gpt6/grok/tdata-session-exporter`.
Создай в нём новую ветку `gpt6-deps` от `origin/main` и работай только в ней.
Живой чекаут `~/github/tdata-session-exporter` НЕ трогать.
**push в origin запрещён** (push-URL клона уже заменён на `no-push`): работу заберёт
постановщик через `git fetch` из клона. Ничего не деплоить, `docker compose up` не
запускать, `.env*` не открывать.

Постановщик до запуска кладёт только эту спеку (`docs/specs/gpt6-deps-bump.md`,
untracked). Больше ничего класть не нужно: тестов в репо нет, сборка идёт из
`Dockerfile` в корне.

## Задача и почему

Общая волна 23.09.2026: OpenAI SDK → 3.19.0, модели gpt-5.6 → gpt-6, Python-образы →
3.14, прочие библиотеки → свежие stable.

В этом репо модели 5.6 нет и OpenAI-вызовов нет вовсе, поэтому работа — ОДИН
коммит зависимостей:

1. `openai==1.70` в `requirements.txt` не используется ни одной строкой кода
   (см. «Проверено»). Бамп мёртвой зависимости через два мажора (1.x → 3.x) только
   добавит в образ httpx2/truststore без пользы. Решение: **удалить `openai` из
   `requirements.txt`**. Ключ `OPENAI_API_KEY` в `.env.SAMPLE` не трогать.
2. Базовый образ `python:3.12.9-slim` (обе стадии) → `python:3.14.7-slim`.
3. Пины поднять до последних stable (проверено реестром PyPI 23.09.2026):

   | пакет | было | стало |
   |---|---|---|
   | telethon | 1.38.1 | 1.45.0 |
   | requests | 2.32.3 | 2.34.2 |
   | python-dotenv | 1.1.0 | 1.2.3 |
   | pysocks | 1.7.1 | 1.7.1 (уже последняя) |

   `opentele @ git+…@1a6f0816…` оставить как есть: апстрим без тегов, последний
   коммит 2024-07-15, это и есть его HEAD — поднимать некуда.

Что может сломаться: opentele собран против старого Telethon и тянет PyQt5 и
TgCrypto (у TgCrypto 1.2.5 на PyPI только sdist — собирается gcc в builder-стадии,
gcc там уже ставится). Если Telethon 1.45.0 ломает импорт или вызовы opentele —
это чинится в этой же вехе (или Telethon остаётся на последней совместимой
версии — см. «Контракт на невыполнимое»).

## Что проверено вживую, а что предположение

- `git grep -n -i openai` по клону: только `requirements.txt:1` и
  `.env.SAMPLE` (комментарий и пустой `OPENAI_API_KEY=`). В `app/handler.py`
  нет ни `import openai`, ни вызовов — проверено чтением импортов (строки 2–9).
- Нет ни одного вхождения `gpt-` в коде — проверено `git grep`.
- Базовая сборка на ЧИСТОМ клоне: `docker build -t gpt6base-tdata .` → rc=0;
  `docker run --rm gpt6base-tdata sh -c 'pip check && python -c "import handler"'` → rc=0.
  База зелёная.
- `handler.py` защищён `if __name__ == "__main__":` — импорт не запускает работу
  (проверено чтением хвоста файла).
- `handler.py` зовёт `TDesktop(...)`, `tdesk.ToTelethon(...)`,
  `functions.account.GetAuthorizationsRequest()`; в базовом образе
  `TDesktop.ToTelethon` имеет сигнатуру `(self, session, flag, api, password, **kwargs)`,
  `API.TelegramDesktop.Generate().api_id` = 2040 — проверено запуском в образе.
- opentele (setup.py на коммите `1a6f081`) требует `pyqt5`, `telethon`, `tgcrypto`
  без версий — проверено чтением его `requirements.txt`.
- `python:3.14.7-slim` существует, дайджест индекса
  `sha256:caaf356f40667c496d405780745b9ac25771c189a51dfcc42430d531ea09f8a2`
  (`docker buildx imagetools inspect`). В проекте принят пин тегом патча без
  дайджеста — так и оставить.
- GitHub Actions (`.github/workflows/ci.yml`) срабатывает только на push в `main`
  и вручную; ветка `gpt6-deps` его не запускает. Сам workflow не трогать.
- **Предположение:** Telethon 1.45.0 совместим с opentele на уровне импорта и
  сигнатур. Проверяется критериями AC-004, живого входа по tdata в вехе нет.

## Что сделать

1. `git checkout -b gpt6-deps origin/main`.
2. `requirements.txt`: удалить строку `openai==1.70`; поднять пины по таблице;
   комментарий про пин opentele сохранить.
3. `Dockerfile`: обе строки `FROM python:3.12.9-slim…` → `FROM python:3.14.7-slim…`
   (имя стадии `AS builder` сохранить). Остальное не менять, если сборка не требует.
4. `README.md`: строку «Python 3.8 или выше» заменить на «Python 3.14 (образ
   `python:3.14.7-slim`)». Больше README не трогать.
5. Собрать образ, прогнать все критерии.
6. Один коммит, в него же — эта спека. Сообщение: `Bump deps and Python to 3.14`
   (≤50 символов, повелительное наклонение, без Co-Authored-By и подписей).

## Не трогать

`app/handler.py` (если сборка и импорт зелёные — правок кода не нужно),
`.github/workflows/ci.yml`, `docker-compose.yml` (там пин дайджеста боевого образа —
его обновляют после осознанного релиза, не в этой вехе), `.env.SAMPLE`, `.gitignore`.
**Исключение:** эта спека `docs/specs/gpt6-deps-bump.md` приезжает untracked и
коммитится вместе с работой.

## Критерии приёмки

Каждая команда запускается из корня клона; rc=0 — критерий выполнен. Тестов в репо
нет: роль полного прогона играет AC-004 (импорт-смоук приложения в собранном образе).

- **AC-001. Состав работы: ветка gpt6-deps, один коммит, только разрешённые файлы, спека закоммичена.**
  `bash -c 'test "$(git rev-parse --abbrev-ref HEAD)" = gpt6-deps && test "$(git rev-list --count origin/main..HEAD)" = 1 && git diff --name-only origin/main HEAD | grep -qx docs/specs/gpt6-deps-bump.md && test -z "$(git diff --name-only origin/main HEAD | grep -v -x -E "Dockerfile|requirements.txt|README.md|docs/specs/gpt6-deps-bump.md")"'`

- **AC-002. Дерево чистое.**
  `bash -c 'test -z "$(git status --porcelain -- . ":(exclude)report.json" ":(exclude)report-blocked.md")"'`

- **AC-003. Пины и базовый образ целевые, openai удалён.**
  `bash -c 'grep -qx "telethon==1.45.0" requirements.txt && grep -qx "requests==2.34.2" requirements.txt && grep -qx "python-dotenv==1.2.3" requirements.txt && ! grep -qi "^openai" requirements.txt && test "$(grep -c "^FROM python:3.14.7-slim" Dockerfile)" = 2 && ! grep -q "python:3.12" Dockerfile'`

- **AC-004. Образ собирается, Python 3.14, pip check чист, приложение и opentele импортируются.**
  `bash -c 'docker build -q -t gpt6-tdata . >/dev/null && docker run --rm gpt6-tdata sh -c "pip check && python -c \"import sys, handler; from opentele.td import TDesktop; from opentele.api import API; assert sys.version_info[:2] == (3, 14), sys.version; assert API.TelegramDesktop.Generate().api_id; assert callable(TDesktop.ToTelethon)\""'`

- **AC-005. В образе нет пакета openai.**
  `bash -c 'docker build -q -t gpt6-tdata . >/dev/null && docker run --rm gpt6-tdata python -c "import importlib.util, sys; sys.exit(importlib.util.find_spec(\"openai\") is not None)"'`

## Авторевью

В этой вехе исполнитель ревьюеров не запускает: веха механическая, дифф —
несколько строк пинов. Ревью диффа, повторный прогон критериев и живую проверку
делает постановщик при приёмке.

## Контракт отчёта

`report.json` в КОРНЕ клона, untracked, не коммитить. Записей ровно пять:
AC-001…AC-005.

```json
{"criteria": [{"id": "AC-001", "status": "pass|fail|blocked",
               "command": "<команда критерия из спеки, посимвольно>", "rc": 0, "note": "…"}]}
```

`blocked` — штатный исход, когда среда не даёт выполнить критерий (нет Docker, нет
сети до PyPI): `"rc": null`, в `note` — дословная ошибка. Обходить несовместимость
запрещено: никаких `--no-deps`, `--ignore-installed`, `--break-system-packages`,
`|| true`, `set +e` в командах.

## Контракт на невыполнимое

Остановись и доложи (в `report.json` и `report-blocked.md`), НЕ обходя, если:

- Telethon 1.45.0 ломает opentele (импорт, `ToTelethon`), а починка требует правки
  кода opentele или больше ~20 строк в `handler.py`. Тогда оставь Telethon на
  последней совместимой версии, критерий AC-003 отметь `fail` с причиной и версией,
  на которой остановился;
- TgCrypto/PyQt5 не собираются или не ставятся на Python 3.14;
- для зелёной сборки нужно менять что-то из «Не трогать».

## Стыки с соседними вехами

После приёмки постановщик забирает ветку и решает о push в `main` (он запустит
GitHub Actions и публикацию образа `:latest` в GHCR) и о новом пине дайджеста в
`docker-compose.yml`. Эта веха ничего из этого не делает.
