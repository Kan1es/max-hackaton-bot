"""Write the API contract to openapi.json at the repository root.

    python scripts/export_openapi.py

The file is generated from the FastAPI app itself, so it cannot describe an
endpoint that does not exist. tests/test_contract.py fails when it drifts
from the code — rerun this script after changing an endpoint or a schema.
"""
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

# Paths in the schema already carry /api/v1, so servers are bare origins.
SERVERS = [
    {"url": "https://maxnalog.ru:8444", "description": "Продакшен (проверка жюри)"},
    {"url": "http://localhost:8000", "description": "Локально, docker compose up"},
]
OUTPUT = ROOT / "openapi.json"


def build_schema() -> dict:
    from app.main import app

    schema = app.openapi()
    return {**schema, "servers": SERVERS}


def render(schema: dict) -> str:
    return json.dumps(schema, ensure_ascii=False, indent=2) + "\n"


if __name__ == "__main__":
    OUTPUT.write_text(render(build_schema()), encoding="utf-8")
    print(f"wrote {OUTPUT.relative_to(ROOT)}")
