# Max Hackathon Backend

FastAPI + PostgreSQL бэкенд сервис с готовой асинхронной архитектурой (SQLAlchemy 2.0 + asyncpg), системой миграций Alembic и контейнеризацией через Docker & Docker Compose.

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
├── docker-compose.yml          # Стек приложения (FastAPI + PostgreSQL)
├── requirements.txt            # Python-зависимости
├── .env.example                # Пример переменных окружения
├── alembic.ini                 # Конфигурация Alembic
├── alembic/
│   ├── env.py                  # Асинхронный запуск миграций
│   └── versions/
│       └── 0001_initial.py     # Начальная миграция всех моделей
└── app/
    ├── main.py                 # Входная точка приложения FastAPI
    ├── core/
    │   ├── config.py           # Настройки проекта (Pydantic Settings)
    │   └── database.py         # Подключение к PostgreSQL (AsyncSession)
    ├── models/                 # SQLAlchemy модели
    │   ├── base.py             # Базовый класс и TimestampMixin
    │   ├── user.py             # Модель пользователей (User)
    │   ├── profile.py          # Модель профилей (Profile)
    │   ├── support_program.py  # Модель мер поддержки (SupportProgram)
    │   └── application.py      # Модель заявок (Application)
    ├── schemas/                # Pydantic схемы (DTO)
    │   ├── health.py
    │   ├── user.py
    │   ├── profile.py
    │   ├── support_program.py
    │   └── application.py
    └── api/
        ├── router.py
        └── v1/
            ├── router.py
            └── endpoints/
                └── health.py   # Эндпоинт проверки здоровья сервиса и БД
```

---

## 🗄 Модели данных

1. **`users` (`User`)**:
   - `id`: Первичный ключ
   - `email`: Уникальный e-mail пользователя
   - `hashed_password`: Хеш пароля (опционально)
   - `role`: Роль (`applicant`, `admin`, `specialist`)
   - `is_active`: Флаг активности
   - `created_at`, `updated_at`: Аудит времени

2. **`profiles` (`Profile`)**:
   - `id`: Первичный ключ
   - `user_id`: Внешний ключ на `users.id` (1-to-1)
   - `first_name`, `last_name`, `middle_name`, `phone`, `birth_date`, `city`, `region`
   - `category`: Категория гражданина/бизнеса (студент, самозанятый, многодетная семья и т.д.)
   - `details`: `JSON` поле для гибких параметров скоринга и матчинга

3. **`support_programs` (`SupportProgram`)**:
   - `id`: Первичный ключ
   - `title`: Название программы
   - `slug`: Уникальный код/слаг
   - `description`: Подробное описание
   - `category`: Направление (субсидии, гранты, льготы и т.д.)
   - `provider`: Организация / ведомство
   - `eligibility_criteria`: `JSON` критерии отбора для алгоритмов подбора
   - `financial_benefit`, `max_amount`: Финансовые параметры
   - `is_active`, `start_date`, `end_date`: Период действия

4. **`applications` (`Application`)**:
   - `id`: Первичный ключ
   - `user_id`: Ссылка на заявителя (`users.id`)
   - `program_id`: Ссылка на программу (`support_programs.id`)
   - `status`: Статус (`draft`, `submitted`, `in_review`, `approved`, `rejected`)
   - `applicant_data`: `JSON` снимок ответов/документов
   - `submitted_at`: Дата отправки
   - `reviewer_notes`: Комментарии проверяющего

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

- **`GET /health`** (и **`GET /api/v1/health`**):
  Возвращает состояние сервиса и статус подключения к PostgreSQL:
  ```json
  {
    "status": "ok",
    "database": "connected",
    "version": "0.1.0"
  }
  ```

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
