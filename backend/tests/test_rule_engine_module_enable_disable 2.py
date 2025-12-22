import pytest
import asyncio
from sqlalchemy.ext.asyncio import AsyncSession
from services.rule_engine import RuleEngine
from models.module import Module
from models.rule import Rule

class DummyResp:
    def __init__(self, json_data, status_code=200):
        self._json = json_data
        self.status_code = status_code
    def json(self):
        return self._json

@pytest.mark.asyncio
async def test_disabled_module_is_skipped(async_session: AsyncSession, monkeypatch):
    # Seed a module disabled
    m = Module(name='sentinel-presidio', display_name='Presidio', enabled=False)
    async_session.add(m)
    await async_session.commit()

    # Create a rule-engine with the test db
    engine = RuleEngine(async_session)

    # Stub DockerManager.list_services to report presidio running
    monkeypatch.setattr(engine.docker_manager, 'list_services', lambda: [{'name':'sentinel-presidio', 'status':'running', 'url':'https://example/analyze'}])

    # Stub httpx.AsyncClient.post to return found_pii True (but since module is disabled it should not be used)
    async def fake_post(url, json):
        return DummyResp({'found_pii': True, 'entities':[{'type':'EMAIL_ADDRESS'}]}, 200)

    monkeypatch.setattr('httpx.AsyncClient.post', fake_post)

    # Create a prompt that would trigger PII
    class Prompt:
        prompt_text = 'Contact me at john.doe@example.com'

    out = await engine.evaluate(Prompt())
    assert out['decision'] == 'ACCEPT'
    assert 'PII Detected' not in out['reason_summary']
