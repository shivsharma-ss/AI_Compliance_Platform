import sys
import os
sys.path.append(os.getcwd())
# Ensure backend package is importable
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
        return [{"name": "sentinel-toxicity", "status": "running", "url": "https://tox.example/predict"}]

class DummyResp:
    def __init__(self):
        self.status_code = 200
    def json(self):
        return {"is_toxic": True}

class FakeAsyncClient:
    def __init__(self, timeout=None):
        pass
    async def __aenter__(self):
        return self
    async def __aexit__(self, exc_type, exc, tb):
        pass
    async def post(self, url, json):
        # ensure the service URL from DockerManager is used
        assert url == "https://tox.example/predict"
        return DummyResp()

@pytest.mark.asyncio
async def test_rule_engine_uses_cloud_service_url(monkeypatch):
    engine = RuleEngine(db=DummySession())
    # Replace the docker manager with our dummy that exposes a cloud URL
    engine.docker_manager = DummyDockerManager()

    # Patch httpx.AsyncClient to our fake client
    monkeypatch.setattr("backend.services.rule_engine.httpx.AsyncClient", FakeAsyncClient)

    class Prompt:
        prompt_text = "I want to kill you"

    out = await engine.evaluate(Prompt())
    assert out["decision"] == "DECLINE"
    assert "Toxic Content Detected" in out["reason_summary"]
