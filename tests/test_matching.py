from app.services import matching
from app.services.matching import (
    REASON_INDUSTRY,
    REASON_PRIORITY,
    REASON_REGION,
    REASON_STATUS,
    match_reasons,
    matches_region,
    program_kind,
    rank_programs,
    status_excluded,
)

from tests.conftest import FakeProfile, FakeProgram


class TestRegion:
    def test_federal_program_matches_any_region(self):
        assert matches_region("Россия", "Краснодарский край")
        assert matches_region("Все регионы РФ", "Москва")

    def test_regional_program_matches_its_own_region_only(self):
        assert matches_region("Москва", "Москва")
        assert not matches_region("Москва", "Санкт-Петербург")

    def test_empty_profile_region_matches_everything(self):
        assert matches_region("Москва", None)


class TestKind:
    def test_loan_wordings_collapse_to_one_kind(self):
        assert program_kind("льготный микрозайм") == "Кредит"
        assert program_kind("льготный кредит") == "Кредит"

    def test_unknown_type_falls_back_to_support(self):
        assert program_kind("нефинансовая помощь") == "Поддержка"
        assert program_kind(None) == "Поддержка"


class TestStatus:
    def test_status_is_actually_used(self, profile):
        """Regression: `status` was collected by the bot and then ignored."""
        program = FakeProgram(
            region="Москва",
            eligible_status="ИП и организации из Единого реестра МСП",
        )
        assert REASON_STATUS in match_reasons(program, profile)

    def test_self_employed_excluded_from_msp_register_programs(self):
        program = FakeProgram(eligible_status="ИП и организации из Единого реестра МСП")
        assert status_excluded(program, "Самозанятый")
        assert not status_excluded(program, "ИП")

    def test_explicit_mention_overrides_the_exclusion(self):
        program = FakeProgram(
            eligible_status="Самозанятые, ИП и организации из реестра МСП"
        )
        assert not status_excluded(program, "Самозанятый")

    def test_no_eligibility_text_never_excludes(self):
        assert not status_excluded(FakeProgram(eligible_status=""), "Самозанятый")


class TestRanking:
    def _catalog(self):
        return [
            FakeProgram(
                id=1, name="Грант для IT", description="цифровые проекты",
                region="Москва", type="грант",
                eligible_status="ИП и организации из реестра МСП",
            ),
            FakeProgram(
                id=2, name="Займ для фермеров", description="сельское хозяйство",
                region="Краснодарский край", type="льготный займ",
                eligible_status="КФХ и ИП-фермеры",
            ),
            FakeProgram(
                id=3, name="Субсидия на туризм", description="отели и гостиницы",
                region="Россия", type="субсидия", eligible_status="ИП и юрлица-МСП",
            ),
        ]

    def test_other_regions_are_filtered_out(self, profile):
        ids = [item.program.id for item in rank_programs(profile, self._catalog())]
        assert 2 not in ids

    def test_best_match_ranks_first(self, profile):
        ranked = rank_programs(profile, self._catalog())
        assert ranked[0].program.id == 1
        assert set(ranked[0].reasons) == {
            REASON_REGION, REASON_INDUSTRY, REASON_PRIORITY, REASON_STATUS
        }

    def test_single_reason_is_not_enough(self):
        thin = FakeProfile(region="Москва")
        assert rank_programs(thin, self._catalog()) == []

    def test_result_is_capped_and_stable(self, profile):
        catalog = self._catalog() * 4
        first = rank_programs(profile, catalog)
        assert len(first) <= matching.TOP_N
        assert [i.program.id for i in first] == [
            i.program.id for i in rank_programs(profile, catalog)
        ]

    def test_scores_are_descending(self, profile):
        scores = [item.score for item in rank_programs(profile, self._catalog())]
        assert scores == sorted(scores, reverse=True)
