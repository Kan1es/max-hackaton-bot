"""Dialog option values.

Mirrors app/core/options.py (backend) and miniapp/src/data/programs.js
`options`. The bot is a separate deployable (own container, own dependency
set from `maxapi`), so it can't import the FastAPI app's package directly —
keep these three lists in sync by hand until they're unified behind a single
`/api/options/` endpoint.
"""

PROFILE_STATUS = ["Самозанятый", "Регистрирую ИП", "ИП"]
PROFILE_REGION = ["Москва", "Московская область", "Краснодарский край", "Санкт-Петербург", "Другой регион"]
PROFILE_INDUSTRY = ["IT", "Услуги", "Торговля", "Производство", "Туризм", "Сельское хозяйство", "Креативные индустрии"]
PROFILE_PRIORITY = ["Развитие", "Деньги на старт", "Льготный займ", "Обучение", "Налоговые льготы"]

OTHER_REGION_LABEL = "Другой регион"
CLASSIFY_CONFIDENCE_THRESHOLD = 0.6
