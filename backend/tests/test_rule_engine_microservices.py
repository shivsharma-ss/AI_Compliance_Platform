import sys
import os
sys.path.append(os.getcwd())
sys.path.append(os.path.join(os.getcwd(), "backend"))
import pytest

from backend.services.rule_engine import RuleEngine

class DummySession:
    async def execute(self, _):
        class Result:
            def scalars(self):
                class S:
                    def all(self):
                        return []
                return S()
        return Result()

class DummyDockerManagerPresidio:
    def list_services(self):
        return [{"name": "sentinel-presidio", "status": "running", "url": "https://pres.example/analyze"}]

class DummyDockerManagerEU:
    def list_services(self):
        return [{"name": "sentinel-eu-ai", "status": "running", "url": "https://eu.example/analyze_risk"}]

class DummyResp:
    def __init__(self, payload):
        self.status_code = 200
        self._payload = payload
    def json(self):
        return self._payload

class FakeAsyncClient:
    def __init__(self, timeout=None):
        pass
    async def __aenter__(self):
        return self
    async def __aexit__(self, exc_type, exc, tb):
        pass
    async def post(self, url, json):
        # Decide which dummy response to return based on URL
        if "pres" in url:
            return DummyResp({"found_pii": True, "entities": [{"type": "PHONE"}]})
        if "eu" in url:
            return DummyResp({"risk_level": "UNACCEPTABLE", "category": "facial recognition", "confidence": 0.8})
        return DummyResp({})

@pytest.mark.asyncio
async def test_presidio_triggers_decline(monkeypatch):
    engine = RuleEngine(db=DummySession())
    engine.docker_manager = DummyDockerManagerPresidio()
    monkeypatch.setattr("backend.services.rule_engine.httpx.AsyncClient", FakeAsyncClient)

    class Prompt:
        prompt_text = "Contact me at 555-1234"

    out = await engine.evaluate(Prompt())
    assert out["decision"] == "DECLINE"
    assert "PII Detected" in out["reason_summary"]

@pytest.mark.asyncio
async def test_eu_ai_triggers_decline(monkeypatch):
    engine = RuleEngine(db=DummySession())
    engine.docker_manager = DummyDockerManagerEU()
    monkeypatch.setattr("backend.services.rule_engine.httpx.AsyncClient", FakeAsyncClient)

    class Prompt:
        prompt_text = "I want to target facial recognition systems"

    out = await engine.evaluate(Prompt())
    assert out["decision"] == "DECLINE"
    assert "EU AI Act Violation" in out["reason_summary"]
