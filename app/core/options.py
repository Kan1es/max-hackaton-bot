"""Canonical dialog options and the keyword corpora the matcher runs on.

This module is the single source of truth. The bot reads it over HTTP at
startup (`GET /api/v1/options/`) and the mini-app fetches the same endpoint,
so option lists are never duplicated by hand again.
"""

PROFILE_STATUS = ["Самозанятый", "Регистрирую ИП", "ИП"]
PROFILE_REGION = ["Москва", "Московская область", "Краснодарский край", "Санкт-Петербург", "Другой регион"]
PROFILE_INDUSTRY = ["IT", "Услуги", "Торговля", "Производство", "Туризм", "Сельское хозяйство", "Креативные индустрии"]
PROFILE_PRIORITY = ["Развитие", "Деньги на старт", "Льготный займ", "Обучение", "Налоговые льготы"]

APPLICATION_STATUS = ["saved", "in_progress", "submitted"]

OTHER_REGION_LABEL = "Другой регион"

# Keyword corpus per industry, used by the rule-based matcher and by the
# /api/v1/classify/ endpoint.
INDUSTRY_KEYWORDS = {
    "IT": ["it", "цифров", "разработк", "онлайн", "интернет", "программного обеспечения"],
    "Услуги": ["услуг", "сервис", "социальн"],
    "Торговля": ["торгов", "рознич"],
    "Производство": ["производ", "промышлен", "обрабатыва"],
    "Туризм": ["туризм", "отел", "гостиниц"],
    "Сельское хозяйство": ["сельск", "агро", "фермер"],
    "Креативные индустрии": ["креатив", "творчес"],
}

# Which program "kind" satisfies which user priority. "Обучение" has no direct
# kind mapping — those programs still surface via region/industry/status reasons.
PRIORITY_KIND_MAP = {
    "Льготный займ": {"Кредит"},
    "Налоговые льготы": {"Льгота"},
    "Деньги на старт": {"Грант", "Субсидия", "Поддержка"},
    "Развитие": {"Грант", "Кредит", "Субсидия"},
}

# Matched against SupportProgram.eligible_status ("допустимый статус
# пользователя" in the source catalog), which is free prose. Terms are
# substrings; wrap a short one in \b-style ambiguity by keeping it >= 4 chars
# or listing a longer form instead ("индивидуальн" rather than "ип").
STATUS_KEYWORDS = {
    "Самозанятый": ["самозанят", "физлиц", "физическ", "граждан"],
    "Регистрирую ИП": [
        "планирующ", "начинающ", "открыть", "регистрац", "не более 24",
        "физлиц", "граждан", "впервые",
    ],
    "ИП": ["индивидуальн", "предпринимат", "мсп", "юрлиц", "организац", "кфх"],
}

# A program is hard-filtered out for a status when its eligibility prose
# contains one of these markers and none of the status' own keywords — e.g. a
# programme open only to the МСП register can't be taken by a self-employed
# person. Keep this list conservative: a false exclusion hides real money.
STATUS_EXCLUSIONS = {
    "Самозанятый": ["реестр мсп", "реестра мсп", "юрлиц", "организац"],
}
