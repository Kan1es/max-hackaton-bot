"""Canonical dialog option values.

These must stay in sync with miniapp/src/data/programs.js `options` — both
the bot buttons and the mini-app dropdowns are meant to offer the exact same
choices so a profile built in chat renders identically once opened in the
mini-app. If you add/rename a value here, update programs.js accordingly
(and vice versa) until the two are unified behind a single API-served config.
"""

PROFILE_STATUS = ["Самозанятый", "Регистрирую ИП", "ИП"]
PROFILE_REGION = ["Москва", "Московская область", "Краснодарский край", "Санкт-Петербург", "Другой регион"]
PROFILE_INDUSTRY = ["IT", "Услуги", "Торговля", "Производство", "Туризм", "Сельское хозяйство", "Креативные индустрии"]
PROFILE_PRIORITY = ["Развитие", "Деньги на старт", "Льготный займ", "Обучение", "Налоговые льготы"]

OTHER_REGION_LABEL = "Другой регион"

# Keyword corpus per industry, used by the rule-based matcher and by the
# /api/classify/ stub. Mirrors industryMatch() in miniapp/src/data/programs.js.
INDUSTRY_KEYWORDS = {
    "IT": ["it", "цифров", "разработк", "онлайн", "интернет", "программного обеспечения"],
    "Услуги": ["услуг", "сервис", "социальн"],
    "Торговля": ["торгов", "рознич"],
    "Производство": ["производ", "промышлен", "обрабатыва"],
    "Туризм": ["туризм", "отел", "гостиниц"],
    "Сельское хозяйство": ["сельск", "агро", "фермер"],
    "Креативные индустрии": ["креатив", "творчес"],
}

# Which program "kind" satisfies which user priority. Mirrors matchReasons()
# in miniapp/src/data/programs.js. "Обучение" has no direct kind mapping
# there either — it still benefits from region/industry match reasons.
PRIORITY_KIND_MAP = {
    "Льготный займ": {"Кредит"},
    "Налоговые льготы": {"Льгота"},
    "Деньги на старт": {"Грант", "Субсидия", "Поддержка"},
    "Развитие": {"Грант", "Кредит", "Субсидия"},
}
