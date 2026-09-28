from app.services.assistant import (
    build_system_prompt,
    fallback_answer,
    keyword_search,
    parse_answer,
)
from tests.conftest import FakeProfile, FakeProgram


def _program(pid, **kwargs):
    program = FakeProgram(id=pid, **kwargs)
    for attr in ("short_title", "conditions", "amount", "deadline", "doc_checklist"):
        setattr(program, attr, kwargs.get(attr))
    return program


class TestParseAnswer:
    def test_programs_line_is_stripped_and_parsed(self):
        answer = parse_answer("Подойдёт грант.\n\nПРОГРАММЫ: 2, 5", known_ids=[1, 2, 5])
        assert answer.text == "Подойдёт грант."
        assert answer.program_ids == [2, 5]

    def test_no_programs_marker(self):
        answer = parse_answer("Не нашёл.\nПРОГРАММЫ: -", known_ids=[1])
        assert answer.program_ids == []
        assert answer.text == "Не нашёл."

    def test_unknown_and_duplicate_ids_are_dropped_and_capped(self):
        answer = parse_answer("x\nПРОГРАММЫ: 1, 1, 42, 2, 3, 4", known_ids=[1, 2, 3, 4])
        assert answer.program_ids == [1, 2, 3]

    def test_markdown_inline_refs_and_chinese_are_cleaned(self):
        answer = parse_answer("**Грант** [3] для 相关业务 бизнеса\nПРОГРАММЫ: 3", known_ids=[3])
        assert answer.text == "Грант для бизнеса"

    def test_marker_appended_to_the_paragraph(self):
        answer = parse_answer("Могу подсказать программы. ПРОГРАММЫ: -", known_ids=[1])
        assert answer.text == "Могу подсказать программы."

    def test_answer_without_marker_is_kept(self):
        answer = parse_answer("Просто ответ", known_ids=[1])
        assert answer.text == "Просто ответ"
        assert answer.program_ids == []


class TestKeywordFallback:
    programs = [
        _program(1, name="Грант для молодых предпринимателей", type="грант"),
        _program(2, name="Льготный займ фонда", type="льготный кредит"),
    ]

    def test_finds_by_word_forms(self):
        assert keyword_search("какие гранты есть?", self.programs) == [1]

    def test_stopwords_only_finds_nothing(self):
        assert keyword_search("как что где", self.programs) == []

    def test_fallback_is_marked_as_stub(self):
        answer = fallback_answer("льготный займ", self.programs)
        assert answer.is_stub is True
        assert answer.program_ids == [2]


def test_prompt_lists_matched_programs_first():
    profile = FakeProfile(status="ИП", region="Москва", industry="IT", priority="Развитие")
    programs = [
        _program(1, name="Сельский грант", region="Краснодарский край", industries=["сельское хозяйство"]),
        _program(2, name="IT грант", region="Москва", industries=["IT"], eligible_status="ИП"),
    ]
    prompt = build_system_prompt(profile, programs)
    assert prompt.index("[2] IT грант — подходит по профилю") < prompt.index("[1] Сельский грант")
    assert "Статус: ИП" in prompt
