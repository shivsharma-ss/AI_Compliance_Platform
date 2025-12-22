import sys
import os
sys.path.append(os.getcwd())
sys.path.append(os.path.join(os.getcwd(), "backend"))

# Ensure required env vars for Settings are present in test env
os.environ.setdefault("DATABASE_URL", "sqlite+aiosqlite:///:memory:")
os.environ.setdefault("SECRET_KEY", "test-secret")

from backend.managers.docker_manager import DockerManager

class Resp:
    def __init__(self, status_code, payload=None):
        self.status_code = status_code
        self._payload = payload
    def json(self):
        if isinstance(self._payload, Exception):
            raise self._payload
        return self._payload

def test_probe_health_model_loaded_false(monkeypatch):
    dm = DockerManager()
    # Simulate a 200 with model_loaded False
    monkeypatch.setattr("backend.managers.docker_manager.httpx.get", lambda url, timeout: Resp(200, {"status": "ok", "model_loaded": False}))
    assert dm._probe_health("https://example", timeout=1.0) is False

def test_probe_health_model_loaded_true(monkeypatch):
    dm = DockerManager()
    monkeypatch.setattr("backend.managers.docker_manager.httpx.get", lambda url, timeout: Resp(200, {"status": "ok", "model_loaded": True}))
    assert dm._probe_health("https://example", timeout=1.0) is True

def test_probe_health_no_json(monkeypatch):
    dm = DockerManager()
    # Simulate 200 but json() raises
    monkeypatch.setattr("backend.managers.docker_manager.httpx.get", lambda url, timeout: Resp(200, Exception("no json")))
    assert dm._probe_health("https://example", timeout=1.0) is True

def test_probe_health_non_200(monkeypatch):
    dm = DockerManager()
    monkeypatch.setattr("backend.managers.docker_manager.httpx.get", lambda url, timeout: Resp(500, {}))
    assert dm._probe_health("https://example", timeout=1.0) is False

def test_probe_health_activated_false(monkeypatch):
    dm = DockerManager()
    monkeypatch.setattr("backend.managers.docker_manager.httpx.get", lambda url, timeout: Resp(200, {"status": "ok", "activated": False}))
    assert dm._probe_health("https://example", timeout=1.0) is False

def test_probe_health_activated_true(monkeypatch):
    dm = DockerManager()
    monkeypatch.setattr("backend.managers.docker_manager.httpx.get", lambda url, timeout: Resp(200, {"status": "ok", "activated": True}))
    assert dm._probe_health("https://example", timeout=1.0) is True
