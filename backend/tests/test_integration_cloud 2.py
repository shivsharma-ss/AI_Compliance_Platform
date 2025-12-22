import os
import pytest
import requests

# This test is gated and will be skipped unless CLOUD_RUN_INTEGRATION is set.
# It expects the following env vars set: BACKEND_URL, TOXICITY_URL, PRESIDIO_URL, EU_AI_URL

BACKEND_URL = os.environ.get("BACKEND_URL")
TOXICITY_URL = os.environ.get("TOXICITY_URL")
PRESIDIO_URL = os.environ.get("PRESIDIO_URL")
EU_AI_URL = os.environ.get("EU_AI_URL")

pytestmark = pytest.mark.skipif(not os.environ.get("CLOUD_RUN_INTEGRATION"), reason="Cloud Run integration not enabled")


def test_toxicity_direct():
    resp = requests.post(f"{TOXICITY_URL}/predict", json={"text": "I want to kill you"}, timeout=10)
    assert resp.status_code == 200
    j = resp.json()
    assert j.get("is_toxic") is True


def test_presidio_direct():
    resp = requests.post(f"{PRESIDIO_URL}/analyze", json={"text": "Call me at 555-1234"}, timeout=10)
    assert resp.status_code == 200
    j = resp.json()
    assert j.get("found_pii") is True


def test_eu_ai_direct():
    resp = requests.post(f"{EU_AI_URL}/analyze_risk", json={"text": "Use facial recognition"}, timeout=10)
    assert resp.status_code == 200
    j = resp.json()
    assert j.get("risk_level") in ["UNACCEPTABLE", "HIGH", "MINIMAL"]


def test_backend_end_to_end():
    # Requires a valid admin token; fetch from metadata server if running in cloud or set via env
    token = os.environ.get("ADMIN_TOKEN")
    assert token is not None

    headers = {"Authorization": f"Bearer {token}"}
    resp = requests.post(f"{BACKEND_URL}/api/v1/prompts/evaluate", json={"prompt_text": "I want to kill you", "intended_use": "integration"}, headers=headers, timeout=10)
    assert resp.status_code == 200
    j = resp.json()
    assert j.get("decision") in ["ACCEPT", "DECLINE"]
