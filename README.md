# 📊 LOG Analyzer

> Веб-приложение для анализа логов Nginx с AI-аналитикой, тёмной темой и CSV-экспортом
---

## Оглавление

- [Возможности](#-возможности)
- [Стек технологий](#-стек-технологий)
- [Быстрый старт](#-быстрый-старт)
- [CLI-режим](#-cli-режим)
- [Архитектура](#-архитектура)
- [API Reference](#-api-reference)
- [Качество кода и CI](#-качество-кода-и-ci)
- [ADR (Architecture Decision Records)](#-adr-architecture-decision-records)

---

## ✅ Возможности

### Реализовано по Заданию

| Требование | Статус | Реализация |
|---|---|---|
| Шаблон имени `nginx-access-ui.log-YYYYMMDD[.gz]` | ✅ | Regex `^nginx-access-ui\.log-(?P<date>\d{8})(?P<ext>\.gz)?$` |
| Plain и gzip логи | ✅ | `gzip.open` / `open` по расширению, автораспаковка при upload |
| Поиск свежего лога по дате в имени (не mtime) | ✅ | `log_finder.py` — `os.scandir`, один проход, O(1) memory |
| Игнорирование логов других сервисов | ✅ | Regex матчит только `nginx-access-ui.log-*`, остальное пропускается |
| Нет логов — не ошибка | ✅ | `log.info("no_logs_found"); return` — чистый выход без `sys.exit(1)` |
| 7 метрик per-URL (`count`, `count_perc`, `time_sum`, `time_perc`, `time_avg`, `time_max`, `time_med`) | ✅ | CLI: `statistics.median()`, Web: SQL `SUM/AVG/MAX` + `statistics.median()` |
| Отчёт `report-YYYY.MM.DD.html` (дата = дата лога) | ✅ | `report_renderer.py` — `string.Template`, `$table_json` |
| `REPORT_SIZE` URL'ов с наибольшим `time_sum` | ✅ | Сортировка по `time_sum` desc → `result[:report_size]`, дефолт 1000 |
| `REPORT_DIR` для готовых отчётов | ✅ | YAML-ключ `REPORT_DIR`, auto-create с `mkdir(parents=True)` |
| jQuery Tablesorter (offline) | ✅ | jQuery 4.0.0 + tablesorter 2.31.3 встроены inline в HTML |
| HTML-отчёт через `string.Template` (`$table_json`) | ✅ | `report_renderer.py` — подстановка JSON, self-contained файл |
| Парсинг `combined` формата Nginx | ✅ | `CombinedLogParser` — regex, generator, O(1) memory |
| CLI-режим: `python -m log_analyzer.cli` | ✅ | Standalone CLI без БД: `--config config.yaml` → HTML-отчёт |
| Порог ошибок парсинга | ✅ | `ERROR_THRESHOLD` — `sys.exit(1)` при превышении |
| `.ts` heartbeat | ✅ | Запись timestamp при успешном завершении |
| `--config` с дефолтным путём | ✅ | Дефолт `./config/config.yaml`; явный `--config` + несуществующий файл → `sys.exit(1)` |
| Файл не существует / не парсится → ошибка | ✅ | `sys.exit(1)` + сообщение; дефолтный путь без файла → silent fallback |
| Идемпотентность | ✅ | Если `report-{date}.html` уже есть → skip |
| Тесты | ✅ | 40 unit tests (pytest), 10 тестов на log_finder |

### Дополнительные фичи

- **Загрузка логов** — `.log`, `.txt`, `.gz` (автораспаковка), дедупликация по SHA-256
- **Smart Upload** — предпросмотр парсинга (preview endpoint) перед загрузкой
- **Статистика** — avg, median, p95, p99 response time; status codes; top endpoints
- **CSV Export** — streaming download, O(1) memory
- **AI-анализ** *(опционально)* — суммаризация + интерактивный SSE-чат (OpenAI / DeepSeek)
- **Тёмная тема** — toggle в header, `localStorage`, плавная анимация
- **Responsive** — адаптивная сетка, auto-collapse sidebar
- **Code Splitting** — `React.lazy()` + `manualChunks` (react 16KB, antd 323KB, query 7.5KB)

---

## 🏗 Стек технологий

| Слой       | Технологии                                                            |
|------------|-----------------------------------------------------------------------|
| Backend    | Python 3.14, FastAPI, SQLAlchemy 2.0 (async), Pydantic v2, Alembic   |
| Frontend   | React 19, TypeScript, Vite 7, Ant Design 6                            |
| Database   | PostgreSQL 17 Alpine                                                  |
| AI         | pydantic-ai-slim (OpenAI, DeepSeek) — graceful degradation без ключей |
| DevOps     | Docker Compose v2, Nginx, GitHub Actions, pre-commit, `uv`, `act`    |
| Workspace  | `uv workspace` — единый lockfile + `.venv` от корня монорепо         |
| Quality    | Ruff, Mypy, ESLint, Interrogate, pip-audit, npm audit, Pytest        |

---

## ⚡️ Быстрый старт

**Требования:** Docker + Docker Compose

```bash
git clone https://github.com/kraspy/log-analyzer.git && cd log-analyzer
cp .env.example .env          # Отредактируй DB_PASSWORD, опционально AI-ключи
docker compose up --build -d
```

| Сервис          | URL                          |
|-----------------|------------------------------|
| Frontend        | http://localhost:3001         |
| Backend API     | http://localhost:8001/health  |
| Swagger / ReDoc | http://localhost:8001/docs    |

```bash
# .env (пример)
DB_PASSWORD=changeme            # Обязательно
OPENAI_API_KEY=sk-...           # Опционально (AI)
DEEPSEEK_API_KEY=sk-...         # Опционально (AI)
```

> AI-функции работают без ключей — приложение отображает fallback-сообщения.

---

## 🖥 CLI-режим

Standalone CLI без Docker и БД — парсинг лога → HTML-отчёт:

```bash
# с пользовательским конфигом:
uv run --project backend python -m log_analyzer.cli --config /path/to/config.yaml

# без --config используется дефолт: ./config/config.yaml
# если файл не найден — используются встроенные дефолты
uv run --project backend python -m log_analyzer.cli
```

```yaml
# config.yaml (все поля опциональны — переопределяют дефолты)
LOG_DIR: /var/log/nginx        # default: /var/log/nginx
REPORT_DIR: ./reports          # default: ./reports
REPORT_SIZE: 1000              # default: 1000
ERROR_THRESHOLD: 0.2           # default: нет порога
LOG_FILE: ./log_analyzer.log   # default: stdout
TS_FILE: ./log_analyzer.ts     # default: нет
```

**Через Docker Compose** (profile `cli`):

```bash
docker compose --profile cli run --rm cli --config /config/config.yaml
```

---

## 🏛 Архитектура

### Общая структура проекта (uv workspace)

```
log_analyzer/                   # uv workspace root
├── pyproject.toml              # [tool.uv.workspace] members = ["backend"]
├── uv.lock                     # Единый lockfile
├── .venv/                      # Единый venv от корня
├── backend/                    # FastAPI, Clean Architecture (workspace member)
│   ├── pyproject.toml          # Зависимости backend
│   ├── src/log_analyzer/
│   │   ├── domain/             # Модели, ABC-интерфейсы (zero deps)
│   │   ├── services/           # Бизнес-логика (parser, statistics, ai)
│   │   ├── infrastructure/     # SQLAlchemy, парсеры, AI providers
│   │   ├── api/                # FastAPI routes + DI (deps.py)
│   │   └── cli/                # CLI entrypoint (без БД)
│   ├── tests/                  # 40+ unit tests
│   ├── alembic/                # DB migrations
│   └── Dockerfile              # Alpine-based (ghcr.io/astral-sh/uv)
├── frontend/
│   ├── src/
│   │   ├── pages/              # Dashboard, Upload, Report
│   │   ├── components/         # AppLayout, ThemeToggle
│   │   ├── contexts/           # ThemeContext (dark mode)
│   │   └── api/client.ts       # Типизированный API-клиент
│   ├── nginx.conf              # Reverse proxy + SSE support
│   └── Dockerfile              # Multi-stage: node build → nginx
├── docker-compose.yml          # 3 сервиса + CLI profile
├── .pre-commit-config.yaml     # 2-tier hooks (commit + push)
├── .github/workflows/ci.yml   # Tier 3: smoke tests
└── Makefile                    # 15 make-команд
```

### Backend — Clean Architecture (4 слоя)

```
Domain  ←──  Services  ←──  Infrastructure / API
(модели, ABC)  (use cases)    (БД, парсеры, HTTP)
```

**Dependency Rule:** каждый слой зависит только от внутренних слоёв. Domain не знает ни про один фреймворк.

| Слой             | Ответственность                                                | Ключевые паттерны                               |
|------------------|----------------------------------------------------------------|-------------------------------------------------|
| `domain/`        | Dataclasses, Enums, ABC-интерфейсы                             | Zero dependencies                               |
| `services/`      | Парсинг, статистика, AI-анализ                                 | `Callable[..., Any]` injection (framework-agnostic) |
| `infrastructure/`| SQLAlchemy ORM, `CombinedLogParser`, AI providers              | ABC implementation, async I/O                    |
| `api/`           | FastAPI routes, `deps.py` (composition root)                   | Dependency Injection, Pydantic validation       |

### Frontend — React SPA

| Аспект         | Реализация                                                      |
|----------------|-----------------------------------------------------------------|
| UI Framework   | Ant Design 6 (`darkAlgorithm` / `defaultAlgorithm`)            |
| Routing        | React Router v7, `React.lazy()` + `Suspense`                   |
| State          | React Context (`ThemeContext`), Server State через `fetch`      |
| Build          | Vite 7, `manualChunks` (vendor splitting)                       |
| Reverse Proxy  | Nginx — `proxy_buffering off` для SSE, `client_max_body_size 200m` |

### Docker Compose

| Сервис     | Образ                                     | Порт    | Описание                      |
|------------|-------------------------------------------|---------|-------------------------------|
| `db`       | postgres:17-alpine                        | —       | Persistent volume, healthcheck|
| `backend`  | ghcr.io/astral-sh/uv:python3.14-alpine    | 8001    | FastAPI + Uvicorn + Alembic   |
| `frontend` | node → nginx                              | 3001    | Multi-stage build             |
| `cli`      | (profile: cli)                            | —       | On-demand, без БД             |

---

## 📡 API Reference

| Method   | Endpoint               | Описание                          |
|----------|------------------------|-----------------------------------|
| `GET`    | `/health`              | Health check                      |
| `POST`   | `/api/logs/upload`     | Загрузка файла (+ `.gz`)         |
| `POST`   | `/api/logs/preview`    | Preview парсинга (до 10 строк)   |
| `GET`    | `/api/reports`         | Список файлов                     |
| `GET`    | `/api/reports/{id}`    | Детали файла                      |
| `DELETE` | `/api/reports/{id}`    | Удаление файла + entries          |
| `GET`    | `/api/stats/{id}`      | Статистика + per-URL stats        |
| `GET`    | `/api/export/{id}/csv` | CSV export (streaming)            |
| `GET`    | `/api/ai/status`       | Статус AI provider                |
| `POST`   | `/api/ai/summary`      | AI суммаризация                   |
| `POST`   | `/api/ai/chat`         | SSE стриминг чат                  |

Подробнее → Swagger UI: http://localhost:8001/docs

---

## 🔒 Качество кода и CI

### 3-Tier CI Strategy (Local-First)

Стратегия минимизирует расход GitHub Actions (~70 % экономии) за счёт максимального исполнения проверок локально.

```
┌─────────────────────────────────────────────────────────────┐
│ Tier 1 — pre-commit (на каждый git commit)                  │
│   Ruff lint/format, Interrogate, ESLint, trailing-whitespace│
│   check-yaml, check-json, check-toml, detect-private-key   │
├─────────────────────────────────────────────────────────────┤
│ Tier 2 — pre-push (на каждый git push)                      │
│   Mypy, Pytest (full), pip-audit, tsc --noEmit,             │
│   npm run build, npm audit                                  │
├─────────────────────────────────────────────────────────────┤
│ Tier 3 — GitHub Actions (remote, smoke only)                │
│   Backend: pytest tests/test_smoke.py                       │
│   Frontend: tsc --noEmit                                    │
└─────────────────────────────────────────────────────────────┘
```

### Pre-commit hooks (`git commit`)

| Hook                  | Тип         | Описание                                   |
|-----------------------|-------------|---------------------------------------------|
| `ruff`                | Auto-fix    | Lint + `--fix`                              |
| `ruff-format`         | Auto-fix    | Форматирование Python                       |
| `interrogate`         | Blocker     | Docstring coverage ≥ 80 %                   |
| `eslint`              | Blocker     | Frontend lint (`--max-warnings=0`)          |
| `trailing-whitespace` | Auto-fix    | Удаление trailing whitespace                |
| `end-of-file-fixer`   | Auto-fix    | Newline в конце файла                       |
| `check-yaml/json/toml`| Blocker    | Валидация конфигов                          |
| `detect-private-key`  | Blocker     | Предотвращение утечки секретов              |

### Pre-push hooks (`git push`)

| Hook             | Описание                                     |
|------------------|-----------------------------------------------|
| `mypy`           | Strict type-checking (backend)                |
| `pytest`         | Full test suite (`-x -q`)                     |
| `pip-audit`      | Python dependency security (OSV)              |
| `tsc --noEmit`   | TypeScript type validation                    |
| `npm run build`  | Frontend production build check               |
| `npm audit`      | Node.js dependency security                   |

### Установка хуков

```bash
make hooks
# или вручную:
uv run pre-commit install
uv run pre-commit install --hook-type pre-push
```

### Локальный запуск CI

```bash
make check-all    # Полный эквивалент pre-push (оба стека)
make ci-local     # Запуск GA workflow через nektos/act
```

### Тесты

```bash
make test         # pytest -v (40+ тестов, ~0.2s)
make test-cov     # + coverage (≥ 55%)
```

| Тест-файл              | Кол-во | Что тестирует                             |
|-------------------------|--------|-------------------------------------------|
| `test_parser.py`        | 7      | Парсинг combined-формата                  |
| `test_parser_service.py`| 6      | Оркестрация: metadata, entries, hash      |
| `test_statistics.py`    | 6      | Перцентили, медианы (чистые функции)      |
| `test_ai_service.py`    | 4      | Graceful degradation без AI               |
| `test_log_finder.py`    | 10     | Поиск свежего лога (CLI)                  |
| `test_config.py`        | 5      | Загрузка YAML-конфигурации (CLI)          |
| `test_smoke.py`         | 2      | Health + OpenAPI (smoke, запускается в GA) |

---

## 📐 ADR (Architecture Decision Records)

### Ключевые архитектурные решения

1. **Clean Architecture** — 4 слоя с Dependency Rule; Domain не зависит от фреймворков
2. **Callable Injection** — сервисы используют `Callable[..., Any]` вместо конкретных AI-фреймворков
3. **Local-First CI** — 3-tier: pre-commit → pre-push → GA smoke (экономия ~70 % GHA minutes)
4. **CLI без БД** — in-memory per-URL статистика, полностью автономный модуль
5. **Streaming everywhere** — CSV export через `StreamingResponse`, AI chat через SSE

---



### Makefile (справочник)

```bash
make lint           # Ruff lint
make format         # Ruff auto-format
make typecheck      # Mypy strict
make test           # Pytest
make test-cov       # Pytest + coverage
make docstrings     # Interrogate (≥ 80%)
make security       # pip-audit + npm audit
make frontend-lint  # ESLint
make frontend-check # TSC + build
make check          # Backend: lint + types + test
make check-all      # Full pre-push (оба стека)
make ci-local       # GA via act
make hooks          # Установка git hooks
make docker-up      # Docker Compose up
make docker-down    # Docker Compose down
```

---

## 📄 Лицензия

MIT
