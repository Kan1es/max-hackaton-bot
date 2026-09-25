from maxapi.context import State, StatesGroup


class ProfileForm(StatesGroup):
    status = State()
    region = State()
    region_custom = State()
    industry = State()
    priority = State()
