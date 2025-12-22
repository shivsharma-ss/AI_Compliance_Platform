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

class DummyDockerManager:
    def list_services(self):
        return [{"name": "sentinel-toxicity", "status": "running", "url": "https://sentinel-toxicity-zflxlqrjwa-ew.a.run.app/predict"}]

class FailClient:
    def __init__(self, timeout=None):
        pass
    async def __aenter__(self):
        return self
    async def __aexit__(self, *args):
        pass
    async def post(self, url, json):
        # Simulate transient failure on first call, success on second call
        if not hasattr(self, "attempt"):
            self.attempt = 1
            raise Exception("Temporary failure in name resolution")
        return type("R", (), {"status_code": 200, "json": lambda self: {"is_toxic": True}})()

@pytest.mark.asyncio
async def test_retry_on_transient_failure(monkeypatch):
    engine = RuleEngine(db=DummySession())
    engine.docker_manager = DummyDockerManager()
    monkeypatch.setattr("backend.services.rule_engine.httpx.AsyncClient", FailClient)

    class Prompt:
        prompt_text = "I want to kill you"

    out = await engine.evaluate(Prompt())
    assert out["decision"] == "DECLINE"
    assert "Toxic Content Detected" in out["reason_summary"]
