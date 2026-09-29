from datetime import date

import httpx
import pytest
import pytest_asyncio
from sqlalchemy import select
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine
from sqlalchemy.pool import StaticPool

from app.collector.base import RawItem, page_text
from app.collector.extract import ExtractedProgram, parse_extraction
from app.collector.sources import msp_rf
from app.collector.sources.msp_rf import GeoBlocked, MspRfSource, known_fields, parse_catalog_page
from app.collector.sync import sync_source
from app.models.base import Base
from app.models.support_program import SupportProgram

TODAY = date(2026, 9, 29)


class TestParseExtraction:
    def test_json_with_prose_and_nested_lists(self):
        content = 'Вот:\n```json\n{"relevant": true, "name": "Грант", "industries": ["it"], ' \
                  '"doc_checklist": ["паспорт", "заявка"], "ends_at": "2026-12-01"}\n```'
        program = parse_extraction(content)
        assert program.name == "Грант"
        assert program.doc_checklist == ["паспорт", "заявка"]
        assert program.ends_at == date(2026, 12, 1)

    def test_bad_date_and_null_lists_are_tolerated(self):
        program = parse_extraction('{"relevant": false, "name": "X", "ends_at": "до конца года", '
                                   '"industries": null, "doc_checklist": "паспорт"}')
        assert program.ends_at is None
        assert program.industries == []
        assert program.doc_checklist == ["паспорт"]

    @pytest.mark.parametrize("content", ["нет данных", '{"relevant": true}', '{"name": ""}', "{broken"])
    def test_unusable(self, content):
        assert parse_extraction(content) is None


def test_page_text_drops_chrome():
    html = "<html><body><header>Меню</header><main><h1>Мера</h1><script>x()</script>" \
           "<p>Условия   участия</p></main><footer>©</footer></body></html>"
    assert page_text(html) == "Мера\nУсловия участия"


CATALOG = """<script>
BX.message({'bitrix_sessid':'abc123'});
var signedParameters = 'SIGNED.sig';
regions = {'x':{'ID':'70','UF_NAME':'г. Москва'},'y':{'ID':'74','UF_NAME':'Краснодарский край'}};
</script>"""


def msp_item(sid, level="federal", finished=False, end="31.12.2026"):
    return {
        "REGION_CODE": "minfin_subsidies", "REGION_SERVICE_ID": str(sid),
        "REGION_SERVICE_NAME": f"Субсидия {sid}", "REGION_SUPPORT_VIEW_NAME": "Предоставление субсидий и грантов",
        "REGION_SUPPORT_DATE_BEGIN": "01.09.2026", "REGION_SUPPORT_DATE_END": end,
        "REGION_SERVICE_IS_FINISHED": finished, "INSTITUTE_TAG_NAME": "Минфин",
        "UF_SERVICE_VIEW_ARRAY": {"XML_ID": level, "VALUE": "Федеральная" if level == "federal" else "Региональная"},
        "URL": "https://promote.budget.gov.ru/x",
    }


class TestMspRf:
    def test_catalog_page(self):
        signed, sessid, regions = parse_catalog_page(CATALOG)
        assert (signed, sessid) == ("SIGNED.sig", "abc123")
        assert regions == {"москва": "70", "краснодарский край": "74"}

    def test_changed_page_is_reported(self):
        with pytest.raises(RuntimeError):
            parse_catalog_page("<html></html>")

    def test_known_fields(self):
        assert known_fields(msp_item(1), "Москва")["region"] == "Россия (все регионы)"
        regional = known_fields(msp_item(2, level="regional", end="15.10.2026"), "Краснодарский край")
        assert regional["region"] == "Краснодарский край"
        assert regional["ends_at"] == date(2026, 10, 15)

    async def test_geo_block_is_reported(self):
        transport = httpx.MockTransport(lambda r: httpx.Response(403, text="<title>доступ запрещен</title>"))
        async with httpx.AsyncClient(transport=transport) as client:
            with pytest.raises(GeoBlocked):
                async for _ in MspRfSource().items(client, 5):
                    pass

    async def test_pages_regions_and_dedup(self, monkeypatch):
        monkeypatch.setattr(msp_rf.settings, "COLLECTOR_MSP_REGIONS", "Москва,Краснодарский край,Марс")
        monkeypatch.setattr(msp_rf.settings, "COLLECTOR_MSP_APPLICANTS", "self")
        monkeypatch.setattr(msp_rf.settings, "COLLECTOR_MSP_VIEWS", "1")
        posts = []

        def handler(request):
            if request.url.path.endswith("/filter/"):
                return httpx.Response(200, text=CATALOG)
            if "ajax.php" in str(request.url):
                form = dict(x.split("=", 1) for x in request.content.decode().split("&"))
                posts.append((form["FILTER%5BREGION%5D"], form["PAGE_SKIP"]))
                assert request.headers["X-Bitrix-Csrf-Token"] == "abc123"
                page = int(form["PAGE_SKIP"])
                items = {1: [msp_item(1), msp_item(2, finished=True)], 2: [msp_item(3, level="regional")]}[page]
                return httpx.Response(200, json={"status": "success", "data": {"items": items, "pages": 2}})
            return httpx.Response(200, text="<main>Подробно. Вы не авторизовались бла Авторизоваться Условия</main>")

        async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
            items = [item async for item in MspRfSource().items(client, 50)]
        # Both known regions, two pages each; the unknown region is skipped.
        assert posts == [("70", "1"), ("70", "2"), ("74", "1"), ("74", "2")]
        # The finished item is dropped; items 1 and 3 are stored once each.
        assert [i.external_id for i in items] == ["minfin_subsidies/1", "minfin_subsidies/3"]
        assert items[1].known["region"] == "Москва"
        assert "Подробно" in items[0].text and "авторизовались" not in items[0].text
        assert items[0].url.endswith("/services/support/minfin_subsidies/1/")

    async def test_limit_stops_early(self, monkeypatch):
        monkeypatch.setattr(msp_rf.settings, "COLLECTOR_MSP_REGIONS", "Москва")
        monkeypatch.setattr(msp_rf.settings, "COLLECTOR_MSP_APPLICANTS", "self")
        monkeypatch.setattr(msp_rf.settings, "COLLECTOR_MSP_VIEWS", "1")

        def handler(request):
            if request.url.path.endswith("/filter/"):
                return httpx.Response(200, text=CATALOG)
            if "ajax.php" in str(request.url):
                return httpx.Response(200, json={"status": "success",
                                                 "data": {"items": [msp_item(i) for i in range(5)], "pages": 1}})
            return httpx.Response(200, text="<main>x</main>")

        async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
            items = [item async for item in MspRfSource().items(client, 2)]
        assert len(items) == 2


# --- sync ---------------------------------------------------------------

class FakeSource:
    name = "fake"

    def __init__(self, items):
        self._items = items

    async def items(self, client, limit):
        for item in self._items[:limit]:
            yield item


def raw(ext_id, text="текст"):
    return RawItem(external_id=ext_id, url=f"https://gov.example/{ext_id}", title=ext_id, text=text)


def extracted(**overrides):
    data = dict(relevant=True, name="Грант на развитие", type="грант", region="Россия (все регионы)",
                eligible_status="субъекты МСП и самозанятые", description="Деньги на развитие")
    data.update(overrides)
    return ExtractedProgram(**data)


class FakeExtractor:
    def __init__(self, result=None):
        self.calls = 0
        self.result = result or extracted()

    async def __call__(self, item):
        self.calls += 1
        return self.result


@pytest_asyncio.fixture
async def session():
    engine = create_async_engine("sqlite+aiosqlite://", connect_args={"check_same_thread": False},
                                 poolclass=StaticPool)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    factory = async_sessionmaker(engine, expire_on_commit=False)
    async with factory() as s:
        s.add(SupportProgram(name="Демо-программа", is_mock=True, is_active=True))
        await s.commit()
        yield s
    await engine.dispose()


async def rows(session, **where):
    result = await session.execute(select(SupportProgram).filter_by(**where))
    return result.scalars().all()


class TestSync:
    async def test_creates_real_programs_and_hides_the_demo(self, session, monkeypatch):
        from app.core.config import settings

        monkeypatch.setattr(settings, "DEMO_CATALOG_MIN_REAL", 1)
        stats = await sync_source(session, FakeSource([raw("a")]), limit=10,
                                  extractor=FakeExtractor(), today=TODAY)
        assert stats.created == 1 and stats.complete
        [program] = await rows(session, source="fake")
        assert program.is_active and not program.is_mock
        assert program.source_url == "https://gov.example/a"
        assert program.checked_at == "2026-09-29"
        [demo] = await rows(session, is_mock=True)
        assert demo.is_active is False

    async def test_unchanged_items_skip_the_llm(self, session):
        extractor = FakeExtractor()
        await sync_source(session, FakeSource([raw("a")]), limit=10, extractor=extractor, today=TODAY)
        stats = await sync_source(session, FakeSource([raw("a")]), limit=10, extractor=extractor, today=TODAY)
        assert extractor.calls == 1
        assert stats.unchanged == 1

    async def test_changed_text_is_extracted_again(self, session):
        extractor = FakeExtractor()
        await sync_source(session, FakeSource([raw("a", "v1")]), limit=10, extractor=extractor, today=TODAY)
        await sync_source(session, FakeSource([raw("a", "v2")]), limit=10, extractor=extractor, today=TODAY)
        assert extractor.calls == 2
        assert len(await rows(session, source="fake")) == 1

    async def test_disappeared_items_are_hidden_after_a_complete_run(self, session):
        await sync_source(session, FakeSource([raw("a"), raw("b")]), limit=10,
                          extractor=FakeExtractor(), today=TODAY)
        await sync_source(session, FakeSource([raw("a")]), limit=10, extractor=FakeExtractor(), today=TODAY)
        [gone] = await rows(session, external_id="b")
        assert gone.is_active is False

    async def test_a_truncated_run_hides_nothing(self, session):
        await sync_source(session, FakeSource([raw("a"), raw("b")]), limit=10,
                          extractor=FakeExtractor(), today=TODAY)
        stats = await sync_source(session, FakeSource([raw("a"), raw("b")]), limit=1,
                                  extractor=FakeExtractor(), today=TODAY)
        assert stats.complete is False
        assert all(p.is_active for p in await rows(session, source="fake"))

    async def test_demo_stays_while_the_real_catalog_is_small(self, session):
        await sync_source(session, FakeSource([raw("a")]), limit=10,
                          extractor=FakeExtractor(), today=TODAY)
        [demo] = await rows(session, is_mock=True)
        assert demo.is_active is True

    async def test_closed_selection_is_hidden(self, session, monkeypatch):
        from app.core.config import settings

        monkeypatch.setattr(settings, "DEMO_CATALOG_MIN_REAL", 1)
        await sync_source(session, FakeSource([raw("a")]), limit=10,
                          extractor=FakeExtractor(extracted(ends_at=date(2026, 9, 1))), today=TODAY)
        [program] = await rows(session, source="fake")
        assert program.is_active is False
        # With nothing real active, the demo catalog comes back.
        [demo] = await rows(session, is_mock=True)
        assert demo.is_active is True

    async def test_irrelevant_items_are_remembered_not_shown(self, session):
        extractor = FakeExtractor(extracted(relevant=False))
        await sync_source(session, FakeSource([raw("a")]), limit=10, extractor=extractor, today=TODAY)
        await sync_source(session, FakeSource([raw("a")]), limit=10, extractor=extractor, today=TODAY)
        [program] = await rows(session, source="fake")
        assert program.is_active is False and program.is_relevant is False
        assert extractor.calls == 1

    async def test_llm_failure_keeps_the_stored_version(self, session):
        await sync_source(session, FakeSource([raw("a", "v1")]), limit=10,
                          extractor=FakeExtractor(), today=TODAY)

        async def failing(item):
            return None

        stats = await sync_source(session, FakeSource([raw("a", "v2")]), limit=10,
                                  extractor=failing, today=TODAY)
        assert stats.failed == 1
        [program] = await rows(session, source="fake")
        assert program.is_active and program.name == "Грант на развитие"

    async def test_source_crash_hides_nothing(self, session):
        await sync_source(session, FakeSource([raw("a")]), limit=10, extractor=FakeExtractor(), today=TODAY)

        class Broken:
            name = "fake"

            async def items(self, client, limit):
                raise GeoBlocked("нет доступа")
                yield  # pragma: no cover

        stats = await sync_source(session, Broken(), limit=10, extractor=FakeExtractor(), today=TODAY)
        assert stats.complete is False
        [program] = await rows(session, source="fake")
        assert program.is_active

    async def test_dry_run_writes_nothing(self, session):
        await sync_source(session, FakeSource([raw("a")]), limit=10, extractor=FakeExtractor(),
                          dry_run=True, today=TODAY)
        assert await rows(session, source="fake") == []


def test_corpmsp_section_links():
    from app.collector.sources.corpmsp import section_links

    html = '<a href="/to-business/">x</a><a href="/to-business/lizing/">a</a>' \
           '<a href="/to-business/sales/kooperatsiya/">b</a><a href="/to-business/lizing/">dup</a>' \
           '<a href="/about/">c</a>'
    assert section_links(html) == ["/to-business/lizing/", "/to-business/sales/kooperatsiya/"]


async def test_a_new_extraction_version_re_extracts_unchanged_items(session, monkeypatch):
    from app.collector import sync

    extractor = FakeExtractor()
    await sync_source(session, FakeSource([raw("a")]), limit=10, extractor=extractor, today=TODAY)
    monkeypatch.setattr(sync, "EXTRACTION_VERSION", "next")
    await sync_source(session, FakeSource([raw("a")]), limit=10, extractor=extractor, today=TODAY)
    assert extractor.calls == 2


async def test_extraction_trusts_the_eligibility_over_the_relevant_flag(monkeypatch):
    from app.collector import extract

    async def fake_chat(messages, **kwargs):
        return '{"relevant": false, "name": "Грант", "eligible_status": "физлица, самозанятые"}'

    monkeypatch.setattr(extract, "chat_completion", fake_chat)
    program = await extract.extract_program(raw("a"))
    assert program.relevant is True



async def test_daily_quota_stops_the_pass_without_hiding(session, monkeypatch):
    from app.services import openrouter

    monkeypatch.setattr(openrouter, "_daily_quota_reset", 0.0)
    await sync_source(session, FakeSource([raw("a"), raw("b")]), limit=10,
                      extractor=FakeExtractor(), today=TODAY)

    extractor = FakeExtractor()

    async def exhausting(item):
        monkeypatch.setattr(openrouter, "_daily_quota_reset", 9e12)
        return None

    stats = await sync_source(session, FakeSource([raw("c", "new"), raw("d", "new")]), limit=10,
                              extractor=exhausting, today=TODAY)
    assert stats.seen == 1 and stats.complete is False
    assert all(p.is_active for p in await rows(session, source="fake"))
    assert extractor.calls == 0



async def test_llm_budget_limits_extractions_but_not_unchanged_items(session):
    extractor = FakeExtractor()
    await sync_source(session, FakeSource([raw("a")]), limit=10, extractor=extractor, today=TODAY)
    items = [raw("a"), raw("b"), raw("c"), raw("d")]
    stats = await sync_source(session, FakeSource(items), limit=10, extractor=extractor,
                              llm_budget=2, today=TODAY)
    # "a" is unchanged (free), "b" and "c" spend the budget, "d" waits.
    assert stats.extracted == 2 and stats.unchanged == 1
    assert stats.complete is False
    assert {p.external_id for p in await rows(session, source="fake")} == {"a", "b", "c"}
