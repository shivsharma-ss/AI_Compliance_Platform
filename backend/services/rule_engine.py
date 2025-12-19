from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from models.rule import Rule
from models.prompt import PromptRequest
import re
import json
import httpx

class RuleEngine:
    def __init__(self, db: AsyncSession):
        self.db = db
        # DockerManager imports settings at module import time which can be problematic in
        # lightweight unit tests (missing env vars). Import lazily to avoid side effects.
        try:
            from managers.docker_manager import DockerManager
            self.docker_manager = DockerManager()
        except Exception:
            self.docker_manager = None

        self.modules_config = {
            "sentinel-presidio": {"url": "http://sentinel-presidio:8000/analyze", "type": "PII"},
            "sentinel-toxicity": {"url": "http://sentinel-toxicity:8000/predict", "type": "TOXICITY"},
            "sentinel-eu-ai": {"url": "http://sentinel-eu-ai:8000/analyze_risk", "type": "EU_AI_ACT"}
        }

    async def evaluate(self, request: PromptRequest) -> dict:
        """
        Evaluates a prompt against active rules and microservices.
        """
        # Fetch active rules (Regex)
        result = await self.db.execute(select(Rule).where(Rule.is_active == True))
        rules = result.scalars().all()
        
        triggered = []
        decision = "ACCEPT"
        reason_summary = "No rules triggered."
        
        # 1. Evaluate Metadata/Regex Rules
        for rule in rules:
            if rule.type == "REGEX":
                payload = rule.payload_json
                pattern = payload.get("pattern")
                if pattern and re.search(pattern, request.prompt_text, re.IGNORECASE):
                    triggered.append(f"Rule: {rule.name}")
                    if rule.severity == "BLOCK":
                        decision = "DECLINE"
        
        # 2. Evaluate Microservices (if active)
        active_services = self.docker_manager.list_services() if self.docker_manager else []
        print(f"RuleEngine active_services: {active_services}")
        
        import urllib.parse
        async with httpx.AsyncClient(timeout=5.0) as client:
            for service in active_services:
                name = service["name"]
                if service["status"] == "running" and name in self.modules_config:
                    config = self.modules_config[name]
                    # Prefer the service URL exposed by DockerManager (used in cloud mode),
                    # otherwise fall back to the local / docker-compose URL defined in modules_config.
                    reported_url = service.get("url") or config.get("url")
                    if not reported_url:
                        # No reachable URL for this service; skip it
                        continue

                    # If the reported URL is only a base (no path), append the module path from config
                    # e.g. reported_url: https://sentinel-presidio...  config['url']: http://sentinel-presidio:8000/analyze
                    # Desired: https://sentinel-presidio.../analyze
                    try:
                        parsed_cfg = urllib.parse.urlparse(config.get("url"))
                        cfg_path = parsed_cfg.path or ""
                    except Exception:
                        cfg_path = ""

                    # Normalize reported_url
                    if urllib.parse.urlparse(reported_url).path in ("", "/") and cfg_path:
                        service_url = reported_url.rstrip('/') + cfg_path
                    else:
                        service_url = reported_url

                    async def try_post(url):
                        return await client.post(url, json={"text": request.prompt_text})

                    # Try once, and retry once on transient network errors
                    resp = None
                    try:
                        resp = await try_post(service_url)
                    except Exception as e1:
                        # Retry once for transient failures
                        try:
                            resp = await try_post(service_url)
                        except Exception as e2:
                            print(f"Failed to query {name} at {service_url}: {e2}")
                            continue

                    if resp and resp.status_code == 200:
                        data = resp.json()

                        # Logic for Presidio
                        if config["type"] == "PII" and data.get("found_pii"):
                            decision = "DECLINE"
                            entities = [e["type"] for e in data.get("entities", [])]
                            triggered.append(f"PII Detected: {', '.join(set(entities))}")

                        # Logic for Toxicity
                        if config["type"] == "TOXICITY" and data.get("is_toxic"):
                            decision = "DECLINE"
                            triggered.append("Toxic Content Detected")

                        # Logic for EU AI Act
                        if config["type"] == "EU_AI_ACT":
                            risk = data.get("risk_level")
                            if risk in ["UNACCEPTABLE", "HIGH"]:
                                decision = "DECLINE"
                                triggered.append(f"EU AI Act Violation: {risk} Risk ({data.get('category')})")
                        # Fail open or closed? For now, just log.

        if triggered:
             # If already declined by regex, keep it. If declined by module, update.
            if decision == "ACCEPT": # If triggered but warn only? (Logic simplified for MVP)
                 pass 
            
            # If any trigger caused a decline
            if "DECLINE" in [decision]: # Redundant check but clear intent
                decision = "DECLINE"
                
            reason_summary = f"Triggered {len(triggered)} checks: " + ", ".join(triggered)

        return {
            "decision": decision,
            "reason_summary": reason_summary,
            "triggered_rules": [] # TODO: Map microservice triggers to rule IDs if we want to persist them similarly
        }

    async def mock_llm_check(self, prompt_text: str):
        pass
