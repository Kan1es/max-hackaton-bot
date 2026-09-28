import hashlib
import hmac
import json
import time
from urllib.parse import urlencode

import pytest

from app.core.security import InitDataError, verify_init_data

TOKEN = "test-token"


def _sign(fields: dict, token: str = TOKEN) -> str:
    check_string = "\n".join(f"{k}={fields[k]}" for k in sorted(fields))
    secret = hmac.new(b"WebAppData", token.encode(), hashlib.sha256).digest()
    signature = hmac.new(secret, check_string.encode(), hashlib.sha256).hexdigest()
    return urlencode({**fields, "hash": signature})


@pytest.fixture
def init_data():
    return _sign({
        "user": json.dumps({"id": 42, "first_name": "Анна"}, ensure_ascii=False),
        "auth_date": str(int(time.time())),
        "query_id": "AAA",
    })


def test_valid_signature_is_accepted(init_data):
    fields = verify_init_data(init_data, TOKEN, max_age=3600)
    assert json.loads(fields["user"])["id"] == 42


def test_tampered_payload_is_rejected(init_data):
    """Swapping the user id — the whole point of the signature check."""
    tampered = init_data.replace("id%22%3A+42", "id%22%3A+43")
    assert tampered != init_data
    with pytest.raises(InitDataError):
        verify_init_data(tampered, TOKEN, max_age=3600)


def test_signature_from_another_token_is_rejected(init_data):
    with pytest.raises(InitDataError):
        verify_init_data(init_data, "someone-elses-token", max_age=3600)


def test_expired_payload_is_rejected():
    stale = _sign({
        "user": json.dumps({"id": 42}),
        "auth_date": str(int(time.time()) - 7200),
    })
    with pytest.raises(InitDataError):
        verify_init_data(stale, TOKEN, max_age=3600)


def test_unsigned_payload_is_rejected():
    with pytest.raises(InitDataError):
        verify_init_data(urlencode({"user": '{"id": 42}'}), TOKEN, max_age=3600)


def test_missing_server_token_is_rejected(init_data):
    with pytest.raises(InitDataError):
        verify_init_data(init_data, "", max_age=3600)
