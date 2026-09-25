# Max Hackathon

«Навигатор мер поддержки» — бот и mini app для MAX, которые помогают самозанятым/ИП находить гранты, льготные займы, субсидии и налоговые льготы. Backend — FastAPI + PostgreSQL (Alembic), диалоговый бот — отдельный сервис на [`maxapi`](bot/README.md), интерфейс mini app — в отдельной папке [`miniapp/`](miniapp/README.md).

## MAX-бот

Диалог сбора профиля (статус → регион → сфера → приоритет), синхронизация с Postgres на каждом шаге, подбор программ и выдача результата — см. [bot/README.md](bot/README.md). Поднимается вместе с остальным стеком через `docker compose up --build` (сервис `bot`).

## Mini app

Локальный запуск интерфейса:

```bash
cd miniapp
npm ci
npm run dev
```

Проверка сборки: `npm run build`. Для отдельного контейнера: `docker build -t max-support-miniapp ./miniapp`. Подробности и ограничения демо описаны в [miniapp/README.md](miniapp/README.md). Интерфейс пока хранит профиль и сохранённые программы в браузере (мок-данные); backend уже предоставляет полноценные `/api/profile/`, `/api/programs/match/{id}` и `/api/applications/` — подключение mini app к этому API вместо локального мока остаётся отдельной задачей.

---

## 🛠 Стек технологий

- **Фреймворк:** [FastAPI](https://fastapi.tiangolo.com/) (Python 3.11+)
- **СУБД:** [PostgreSQL 16](https://www.postgresql.org/)
- **ORM:** [SQLAlchemy 2.0](https://docs.sqlalchemy.org/) (AsyncIO engine + asyncpg)
- **Миграции:** [Alembic](https://alembic.sqlalchemy.org/) (с поддержкой async engine)
- **Валидация данных:** [Pydantic v2](https://docs.pydantic.dev/) + [Pydantic-Settings](https://docs.pydantic.dev/latest/concepts/pydantic_settings/)
- **Контейнеризация:** Docker & Docker Compose

---

## 📁 Структура проекта

```text
.
├── Dockerfile                  # Описание сборки контейнера FastAPI
├── docker-compose.yml          # Стек приложения (FastAPI + PostgreSQL + бот)
├── bot/                        # MAX-бот (диалог, maxapi) — см. bot/README.md
├── miniapp/                    # React/Vite mini app с отдельным Dockerfile
├── requirements.txt            # Python-зависимости backend
├── .env.example                # Пример переменных окружения (backend + бот)
├── alembic.ini                 # Конфигурация Alembic
├── alembic/
│   ├── env.py                  # Асинхронный запуск миграций
│   └── versions/
│       └── 0001_initial.py     # Начальная миграция всех моделей
└── app/
    ├── main.py                 # Входная точка FastAPI + автосидинг мок-каталога программ
    ├── core/
    │   ├── config.py           # Настройки проекта (Pydantic Settings)
    │   ├── options.py          # Канонические варианты диалога (в т.ч. для бота/mini app)
    │   └── database.py         # Подключение к PostgreSQL (AsyncSession)
    ├── db/
    │   ├── seed.py             # Загрузка мок-каталога программ при первом старте
    │   └── seed_data/support_programs.json
    ├── services/
    │   └── matching.py         # Rule-based подбор программ (регион+сфера+приоритет)
    ├── models/                 # SQLAlchemy модели
    │   ├── base.py             # Базовый класс и TimestampMixin
    │   ├── user.py             # Пользователь MAX (User)
    │   ├── profile.py          # Профиль, собранный ботом (Profile)
    │   ├── support_program.py  # Каталог мер поддержки (SupportProgram)
    │   ├── match.py            # Результаты подбора (Match)
    │   └── application.py      # «Мои заявки» (Application)
    ├── schemas/                # Pydantic схемы (DTO)
    └── api/
        ├── router.py
        └── v1/
            ├── router.py
            └── endpoints/
                ├── health.py       # Проверка здоровья сервиса и БД
                ├── profiles.py     # POST /api/profile/
                ├── programs.py     # GET /api/programs/match/{id}, /api/programs/{id}
                ├── applications.py # POST/GET /api/applications/
                └── classify.py     # POST /api/classify/ (заглушка NLP)
```

---

## 🗄 Модели данных

1. **`users` (`User`)**:
   - `id`: Первичный ключ
   - `max_user_id`: Уникальный идентификатор пользователя в MAX
   - `created_at`: Аудит времени

2. **`profiles` (`Profile`)** — заполняется ботом по шагам, поля nullable до завершения диалога:
   - `id`, `user_id` (FK → `users.id`, 1-to-1)
   - `status`: `Самозанятый` / `Регистрирую ИП` / `ИП`
   - `region`: регион работы
   - `industry`: сфера деятельности
   - `priority`: `Развитие` / `Деньги на старт` / `Льготный займ` / `Обучение` / `Налоговые льготы`

   Варианты значений — единый источник [`app/core/options.py`](app/core/options.py), синхронизированный с ботом (`bot/options.py`) и mini app (`miniapp/src/data/programs.js`).

3. **`support_programs` (`SupportProgram`)** — каталог мер поддержки:
   - `id`, `name`, `description`, `region`, `industries[]`, `conditions`, `type` (вид поддержки — грант/кредит/субсидия/льгота), `amount`, `deadline`, `doc_checklist[]`, `source_url`
   - `is_mock`: `True` — данные пока тестовый снапшот (см. `app/db/seed_data/support_programs.json`, 19 программ)

4. **`matches` (`Match`)** — история подбора для аналитики:
   - `id`, `profile_id` (FK), `program_id` (FK), `score`, `created_at`

5. **`applications` (`Application`)** — «Мои заявки»:
   - `id`, `profile_id` (FK), `program_id` (FK), `status` (`saved` / `in_progress` / `submitted`), `created_at`

---

## 🚀 Быстрый старт

### Вариант 1: Запуск через Docker Compose (Рекомендуемый)

1. Скопируйте конфигурацию окружения:
   ```bash
   cp .env.example .env
   ```

2. Запустите сервис и базу данных:
   ```bash
   docker compose up --build
   ```

3. Сервис станет доступен:
   - **Swagger Документация:** http://localhost:8000/docs
   - **ReDoc:** http://localhost:8000/redoc
   - **Health Check:** http://localhost:8000/health (а также http://localhost:8000/api/v1/health)

---

### Вариант 2: Локальный запуск (без Docker)

1. Создайте и активируйте виртуальное окружение:
   ```bash
   python3 -m venv .venv
   source .venv/bin/activate
   ```

2. Установите зависимости:
   ```bash
   pip install -r requirements.txt
   ```

3. Настройте `.env` файл с вашим локальным PostgreSQL:
   ```bash
   cp .env.example .env
   # Отредактируйте параметры подключения в .env при необходимости
   ```

4. Примените миграции:
   ```bash
   alembic upgrade head
   ```

5. Запустите сервер разработки:
   ```bash
   uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
   ```

---

## 📡 Эндпоинты

Базовый путь: `/api/v1`.

- **`GET /health`** (и **`GET /api/v1/health`**):
  Возвращает состояние сервиса и статус подключения к PostgreSQL:
  ```json
  {
    "status": "ok",
    "database": "connected",
    "version": "0.1.0"
  }
  ```
- **`POST /api/v1/profile/`** — создать/частично обновить профиль по `max_user_id` (вызывается ботом после каждого шага диалога).
- **`GET /api/v1/profile/by-max-user/{max_user_id}`** — получить профиль по идентификатору пользователя MAX.
- **`GET /api/v1/programs/`** — список всех программ каталога.
- **`GET /api/v1/programs/match/{profile_id}`** — топ-3 подходящие программы (rule-based, см. [`app/services/matching.py`](app/services/matching.py)); результат сохраняется в `matches`.
- **`GET /api/v1/programs/{id}`** — карточка программы.
- **`POST /api/v1/applications/`** — сохранить программу в «Мои заявки».
- **`GET /api/v1/applications/{profile_id}`** — список сохранённых заявок профиля.
- **`POST /api/v1/classify/`** — определение сферы деятельности по свободному тексту. Пока заглушка на ключевых словах (`app/api/v1/endpoints/classify.py`) — интеграция настоящей модели (rubert-tiny2) отдельным этапом.

---

## 🔄 Миграции базы данных (Alembic)

- **Создать новую автоматическую миграцию после изменения моделей:**
  ```bash
  alembic revision --autogenerate -m "describe changes"
  ```
- **Применить все миграции к базе данных:**
  ```bash
  alembic upgrade head
  ```
- **Откатить последнюю миграцию:**
  ```bash
  alembic downgrade -1
  ```
