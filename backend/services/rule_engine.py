from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from models.rule import Rule
from models.prompt import PromptRequest
import re
import json
import httpx
from managers.docker_manager import DockerManager

class RuleEngine:
    def __init__(self, db: AsyncSession):
        self.db = db
        self.docker_manager = DockerManager()
        self.modules_config = {
            "spotixx-presidio": {"url": "http://spotixx-presidio:8000/analyze", "type": "PII"},
            "spotixx-toxicity": {"url": "http://spotixx-toxicity:8000/predict", "type": "TOXICITY"}
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
        active_services = self.docker_manager.list_services()
        
        async with httpx.AsyncClient(timeout=3.0) as client:
            for service in active_services:
                name = service["name"]
                if service["status"] == "running" and name in self.modules_config:
                    config = self.modules_config[name]
                    try:
                        resp = await client.post(config["url"], json={"text": request.prompt_text})
                        if resp.status_code == 200:
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
                                
                    except Exception as e:
                        print(f"Failed to query {name}: {e}")
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
