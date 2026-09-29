"""The published API contract matches the code.

- openapi.json is what FastAPI generates right now (rerun
  scripts/export_openapi.py after changing an endpoint or schema);
- every check in DATA-API.yaml passes, in order, against the real app with
  production auth settings and the real demo catalog — the same run the
  judges' platform performs against the deployed URL.
"""
import json
import re
import sys
from pathlib import Path

import pytest
import pytest_asyncio
import yaml
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine
from sqlalchemy.pool import StaticPool

from app.core.config import settings
from app.core.database import get_db
from app.main import app
from app.models.base import Base
from app.models.support_program import SupportProgram

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))
import export_openapi  # noqa: E402

SERVICE_TOKEN = "contract-service-token"
CONTRACT = yaml.safe_load((ROOT / "DATA-API.yaml").read_text(encoding="utf-8"))


def test_openapi_file_is_current():
    on_disk = (ROOT / "openapi.json").read_text(encoding="utf-8")
    assert on_disk == export_openapi.render(export_openapi.build_schema()), (
        "openapi.json is stale — run: python scripts/export_openapi.py"
    )


def test_contract_paths_exist_in_openapi():
    spec = json.loads((ROOT / "openapi.json").read_text(encoding="utf-8"))
    prefix = "/api/v1"
    documented = {
        (method.upper(), re.sub(r"\{[^}]+\}", "{}", path))
        for path, ops in spec["paths"].items()
        for method in ops
    }
    for check in CONTRACT["checks"] + CONTRACT["optional_checks"]:
        path = re.sub(r"\{[^}]+\}|/\d+(?=/|$)", "/{}", prefix + check["path"]).replace("//", "/")
        assert (check["method"], path) in documented, check["id"]


@pytest_asyncio.fixture
async def client(monkeypatch):
    monkeypatch.setattr(settings, "REQUIRE_SIGNED_INIT_DATA", True)
    monkeypatch.setattr(settings, "SERVICE_TOKEN", SERVICE_TOKEN)

    engine = create_async_engine(
        "sqlite+aiosqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool
    )
    session_factory = async_sessionmaker(engine, expire_on_commit=False)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    catalog = json.loads((ROOT / CONTRACT["test_data"]["catalog"]).read_text(encoding="utf-8"))
    async with session_factory() as session:
        session.add_all(SupportProgram(**row) for row in catalog)
        await session.commit()

    async def override_get_db():
        async with session_factory() as session:
            yield session

    app.dependency_overrides[get_db] = override_get_db
    base = CONTRACT["base_url"].split("://", 1)[1].split("/", 1)[1]
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url=f"http://test/{base}"
    ) as http:
        yield http
    app.dependency_overrides.clear()
    await engine.dispose()


def _fill(value, saved):
    """Substitute ${SERVICE_TOKEN} and {saved_name}; a whole-string
    placeholder keeps the saved value's type (so program_id stays an int)."""
    if isinstance(value, dict):
        return {k: _fill(v, saved) for k, v in value.items()}
    if isinstance(value, list):
        return [_fill(v, saved) for v in value]
    if not isinstance(value, str):
        return value
    value = value.replace("${SERVICE_TOKEN}", SERVICE_TOKEN)
    whole = re.fullmatch(r"\{(\w+)\}", value)
    if whole and whole.group(1) in saved:
        return saved[whole.group(1)]
    return re.sub(r"\{(\w+)\}", lambda m: str(saved.get(m.group(1), m.group(0))), value)


def _extract(body, expr: str):
    """The two JSONPath shapes the contract uses: $.field and $[n].field."""
    match = re.fullmatch(r"\$(?:\[(\d+)\])?\.(\w+)", expr)
    assert match, f"unsupported path {expr}"
    if match.group(1) is not None:
        body = body[int(match.group(1))]
    return body[match.group(2)]


def _check_response(check, response):
    spec = check.get("response") or {}
    if spec.get("body") == "empty":
        assert response.content == b""
        return
    if "content_type" in spec:
        assert response.headers["content-type"].startswith(spec["content_type"])
    body = response.json()
    if spec.get("type") == "array":
        assert isinstance(body, list)
        assert len(body) >= spec.get("min_items", 0)
        assert len(body) <= spec.get("max_items", len(body))
        for item in body:
            missing = set(spec.get("item_required_fields", [])) - item.keys()
            assert not missing, missing
    else:
        missing = set(spec.get("required_fields", [])) - body.keys()
        assert not missing, missing
    for key, expected in (spec.get("equals") or {}).items():
        assert body[key] == expected, (key, body[key])


@pytest.mark.asyncio
@pytest.mark.parametrize("run", [1, 2], ids=["first-run", "repeat-run"])
async def test_data_api_checks_pass(client, run):
    """Two passes in one database: the contract promises repeatable results."""
    saved: dict = {}
    for _ in range(run):
        for check in CONTRACT["checks"]:
            params = _fill(check.get("params") or {}, saved)
            path = _fill(check["path"], saved)
            for name, value in (params.get("path") or {}).items():
                path = path.replace("{" + name + "}", str(value))
            headers = _fill(CONTRACT["roles"][check["role"]]["headers"], saved)

            response = await client.request(
                check["method"],
                path.lstrip("/"),
                params=params.get("query"),
                json=params.get("body"),
                headers=headers,
            )
            assert response.status_code in check["expected_status"], (
                check["id"], response.status_code, response.text,
            )
            _check_response(check, response)
            for name, expr in (check.get("save") or {}).items():
                saved[name] = _extract(response.json(), expr)
