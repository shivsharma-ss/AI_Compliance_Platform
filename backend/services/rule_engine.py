from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from models.rule import Rule
from models.prompt import PromptRequest
import logging
import re
import json
import httpx
from managers.docker_manager import DockerManager

logger = logging.getLogger(__name__)

class RuleEngine:
    def __init__(self, db: AsyncSession):
        """
        Create a RuleEngine instance and configure its runtime dependencies.
        
        Initializes and stores the database session, creates a DockerManager for service discovery, and defines the mapping of supported microservices to their endpoint URLs and evaluation types:
        - "spotixx-presidio": PII analysis endpoint
        - "spotixx-toxicity": toxicity prediction endpoint
        - "spotixx-eu-ai": EU AI Act risk analysis endpoint
        
        Parameters:
            db (AsyncSession): Async database session used for querying and persisting rule data.
        """
        self.db = db
        self.docker_manager = DockerManager()
        self.modules_config = {
            "spotixx-presidio": {
                "url": "http://spotixx-presidio:8000/analyze",
                "type": "PII",
                "fail_closed": False,
            },
            "spotixx-toxicity": {
                "url": "http://spotixx-toxicity:8000/predict",
                "type": "TOXICITY",
                "fail_closed": False,
            },
            "spotixx-eu-ai": {
                "url": "http://spotixx-eu-ai:8000/analyze_risk",
                "type": "EU_AI_ACT",
                "fail_closed": False,
            },
        }

    def _notify_monitoring(self, service_name: str, error: Exception) -> None:
        logger.warning(
            "Monitoring alert: rule service failure",
            extra={"service": service_name, "error": str(error)},
        )

    async def evaluate(self, request: PromptRequest) -> dict:
        """
        Evaluate a prompt against active regex-based rules and configured microservices to produce a moderation decision.
        
        Checks active REGEX rules from the database and queries running microservices (PII, TOXICITY, EU_AI_ACT) to determine whether the prompt should be accepted or declined. Triggers are collected from any matching rules or microservice responses and summarized in the returned result.
        
        Parameters:
            request (PromptRequest): The prompt evaluation request containing the text to inspect and any associated metadata.
        
        Returns:
            dict: Evaluation outcome with keys:
                - decision (str): "ACCEPT" or "DECLINE" indicating the final moderation decision.
                - reason_summary (str): Human-readable summary of triggered checks and reasons.
                - triggered_rules (list): Placeholder list for triggered rule identifiers (currently empty).
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

                            # Logic for EU AI Act
                            if config["type"] == "EU_AI_ACT":
                                risk = data.get("risk_level")
                                if risk in ["UNACCEPTABLE", "HIGH"]:
                                    decision = "DECLINE"
                                    triggered.append(f"EU AI Act Violation: {risk} Risk ({data.get('category')})")
                                
                    except Exception as e:
                        fail_closed = config.get("fail_closed", False)
                        logger.error("Failed to query service", exc_info=True, extra={"service": name})
                        self._notify_monitoring(name, e)
                        if fail_closed:
                            decision = "DECLINE"
                            triggered.append(f"Service Failure: {name}")
                        continue

        if triggered:
            reason_summary = f"Triggered {len(triggered)} checks: " + ", ".join(triggered)

        return {
            "decision": decision,
            "reason_summary": reason_summary,
            "triggered_rules": [] # TODO: Map microservice triggers to rule IDs if we want to persist them similarly
        }

    async def mock_llm_check(self, prompt_text: str):
        """
        Placeholder for an LLM-based safety check for the given prompt text.
        
        Reserved for integrating a language-model safety evaluation of prompt_text; currently a no-op with no observable effect.
        """
        pass