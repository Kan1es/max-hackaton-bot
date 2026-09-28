"""The catalog is hand-maintained JSON, so guard its shape."""
import json

from app.db.seed import SEED_FILE
from app.models.support_program import SupportProgram

REQUIRED = ["name", "description", "region", "type", "eligible_status"]


def _catalog():
    return json.loads(SEED_FILE.read_text(encoding="utf-8"))


def test_catalog_is_not_empty():
    assert len(_catalog()) == 19


def test_every_row_maps_onto_the_model():
    columns = set(SupportProgram.__table__.columns.keys())
    for row in _catalog():
        unknown = set(row) - columns
        assert not unknown, f"{row['name']}: unknown fields {unknown}"


def test_required_fields_are_present_and_filled():
    for row in _catalog():
        for field in REQUIRED:
            assert row.get(field), f"{row.get('name')}: missing {field}"


def test_list_fields_are_lists():
    for row in _catalog():
        assert isinstance(row["industries"], list)
        assert isinstance(row["doc_checklist"], list)


def test_citation_markers_were_stripped():
    raw = SEED_FILE.read_text(encoding="utf-8")
    assert "[web:" not in raw


def test_names_are_unique():
    """seed_support_programs() syncs rows by name, so duplicates would clash."""
    names = [row["name"] for row in _catalog()]
    assert len(names) == len(set(names))


def test_sources_are_https():
    for row in _catalog():
        assert row["source_url"].startswith("https://"), row["name"]
