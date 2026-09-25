# MAX-бот «Навигатор мер поддержки»

Диалоговый бот на [`maxapi`](https://github.com/max-messenger/max-botapi-python) (MAX-team-verified форк). Собирает профиль пользователя за 4 коротких шага (статус → регион → сфера → приоритет), на каждом шаге синхронизирует профиль с backend (`POST /api/profile/`), затем вызывает подбор программ (`GET /api/programs/match/{profile_id}`) и либо отвечает прямо в чате (1 программа), либо предлагает открыть мини-апп для сравнения (2-3 программы).

## Получение токена

1. Напишите `@MasterBot` в MAX, создайте бота — получите токен.
2. Документация API: https://dev.max.ru/docs-api

## Локальный запуск (без Docker)

```bash
cd max-hackaton
cp .env.example .env
# впишите MAX_BOT_TOKEN в .env, backend должен быть поднят на localhost:8000

pip install -r bot/requirements.txt
python -m bot.main
```

По умолчанию бот работает через long polling (`USE_WEBHOOK=False` в `.env`) — токен не должен быть одновременно подписан на webhook (`bot.delete_webhook()` вызывается автоматически при старте).

## Запуск через Docker Compose

```bash
docker compose up --build
```

Поднимет `db` + `web` (FastAPI) + `bot` одной командой; бот обращается к backend по внутреннему адресу `http://web:8000/api/v1` (см. `docker-compose.yml`).

## Структура

| Файл | Назначение |
|---|---|
| `main.py` | Точка входа: инициализация `Bot`/`Dispatcher`, polling/webhook |
| `dialog.py` | Хендлеры диалога (FSM по шагам профиля) + выдача результатов |
| `states.py` | Состояния FSM (`ProfileForm`) |
| `keyboards.py` | Инлайн-клавиатуры для каждого шага |
| `options.py` | Варианты ответов — должны совпадать с `app/core/options.py` и `miniapp/src/data/programs.js` |
| `api_client.py` | HTTP-клиент к FastAPI backend |
| `config.py` | Настройки из `.env` (`pydantic-settings`) |

## Известные ограничения MVP

- Шаг «сфера деятельности» умеет принимать свободный текст, но реальная NLP-классификация (rubert-tiny2) ещё не подключена — сейчас на бэкенде стоит заглушка (`POST /api/classify/`, см. `app/api/v1/endpoints/classify.py`), которая всегда просит подтвердить сферу кнопками. Как появится настоящая модель — порог `CLASSIFY_CONFIDENCE_THRESHOLD` в `options.py` начнёт реально работать.
- Кнопка «Сравнить в приложении» использует `OpenAppButton` — для реальной работы мини-апп должен быть зарегистрирован в настройках бота на dev.max.ru (`web_app`/`contact_id` берутся из `bot.me`).
- Состояние диалога (`MemoryContext`) хранится в памяти процесса — рестарт бота сбрасывает незавершённые (не сохранённые в БД) диалоги. Для прод-нагрузки стоит вынести в Redis/БД.
