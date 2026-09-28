import httpx
import pytest

from app.core.config import settings
from app.services import openrouter
from app.services.llm_classifier import _parse_answer, classify_with_llm


class TestParseAnswer:
    def test_plain_json(self):
        assert _parse_answer('{"industry": "IT", "confidence": 0.9}') == ("IT", 0.9)

    def test_fenced_json_with_prose(self):
        content = 'Думаю так:\n```json\n{"industry": "Туризм", "confidence": 0.7}\n```'
        assert _parse_answer(content) == ("Туризм", 0.7)

    def test_null_industry_is_a_valid_no(self):
        assert _parse_answer('{"industry": null, "confidence": 0.2}') == (None, 0.0)

    def test_unknown_industry_is_unusable(self):
        assert _parse_answer('{"industry": "Космос", "confidence": 0.9}') is None

    def test_garbage_is_unusable(self):
        assert _parse_answer("не знаю") is None

    def test_confidence_is_clamped(self):
        assert _parse_answer('{"industry": "IT", "confidence": 5}') == ("IT", 1.0)


def _mock_transport(monkeypatch, handler):
    real_client = httpx.AsyncClient

    def factory(*args, **kwargs):
        kwargs["transport"] = httpx.MockTransport(handler)
        return real_client(*args, **kwargs)

    monkeypatch.setattr(openrouter.httpx, "AsyncClient", factory)
    monkeypatch.setattr(openrouter, "RATE_LIMIT_RETRY_DELAY", 0)


class TestClassifyWithLlm:
    async def test_disabled_without_key(self):
        assert await classify_with_llm("пеку торты") is None

    async def test_success(self, monkeypatch):
        monkeypatch.setattr(settings, "OPENROUTER_API_KEY", "k")
        seen = {}

        def handler(request):
            seen["auth"] = request.headers["authorization"]
            return httpx.Response(200, json={"choices": [{"message": {
                "content": '{"industry": "Услуги", "confidence": 0.8}'}}]})

        _mock_transport(monkeypatch, handler)
        assert await classify_with_llm("стригу собак") == ("Услуги", 0.8)
        assert seen["auth"] == "Bearer k"

    @pytest.mark.parametrize("response", [
        httpx.Response(429, json={"error": "rate limited"}),
        httpx.Response(200, json={"choices": []}),
        httpx.Response(200, text="not json"),
    ])
    async def test_failures_return_none(self, monkeypatch, response):
        monkeypatch.setattr(settings, "OPENROUTER_API_KEY", "k")
        _mock_transport(monkeypatch, lambda request: response)
        assert await classify_with_llm("что-то") is None


class TestOpenRouterClient:
    async def test_reasoning_is_disabled_and_fallbacks_are_sent(self, monkeypatch):
        monkeypatch.setattr(settings, "OPENROUTER_API_KEY", "k")
        monkeypatch.setattr(settings, "OPENROUTER_MODEL", "a:free, b:free")
        seen = {}

        def handler(request):
            import json
            seen.update(json.loads(request.content))
            return httpx.Response(200, json={"choices": [{"message": {"content": " ok "}}]})

        _mock_transport(monkeypatch, handler)
        content = await openrouter.chat_completion(
            [{"role": "user", "content": "hi"}], max_tokens=10, timeout=5
        )
        assert content == "ok"
        assert seen["reasoning"] == {"enabled": False}
        assert seen["model"] == "a:free"
        assert seen["models"] == ["a:free", "b:free"]

    async def test_rate_limit_is_retried(self, monkeypatch):
        monkeypatch.setattr(settings, "OPENROUTER_API_KEY", "k")
        calls = []

        def handler(request):
            calls.append(1)
            if len(calls) < 3:
                return httpx.Response(429, json={"error": "busy"})
            return httpx.Response(200, json={"choices": [{"message": {"content": "готово"}}]})

        _mock_transport(monkeypatch, handler)
        content = await openrouter.chat_completion(
            [{"role": "user", "content": "hi"}], max_tokens=10, timeout=10
        )
        assert content == "готово"
        assert len(calls) == 3

    async def test_empty_content_is_no_answer(self, monkeypatch):
        monkeypatch.setattr(settings, "OPENROUTER_API_KEY", "k")
        _mock_transport(monkeypatch, lambda request: httpx.Response(
            200, json={"choices": [{"message": {"content": None}}]}))
        assert await openrouter.chat_completion(
            [{"role": "user", "content": "hi"}], max_tokens=10, timeout=5
        ) is None
