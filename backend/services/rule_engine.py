from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from models.rule import Rule
from models.prompt import PromptRequest
import re
import json

class RuleEngine:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def evaluate(self, request: PromptRequest) -> dict:
        """
        Evaluates a prompt against active rules.
        Returns evaluation result dict.
        """
        # Fetch active rules
        result = await self.db.execute(select(Rule).where(Rule.is_active == True))
        rules = result.scalars().all()
        
        triggered = []
        decision = "ACCEPT"
        reason_summary = "No rules triggered."
        
        for rule in rules:
            if rule.type == "REGEX":
                payload = rule.payload_json
                pattern = payload.get("pattern")
                if pattern and re.search(pattern, request.prompt_text, re.IGNORECASE):
                    triggered.append(rule)
                    if rule.severity == "BLOCK":
                        decision = "DECLINE"
        
        if triggered:
            # Prioritize BLOCK decision
            if any(r.severity == "BLOCK" for r in triggered):
                decision = "DECLINE"
            
            reason_summary = f"Triggered {len(triggered)} rules: " + ", ".join([r.name for r in triggered])

        return {
            "decision": decision,
            "reason_summary": reason_summary,
            "triggered_rules": [r.id for r in triggered]
        }

    async def mock_llm_check(self, prompt_text: str):
        # TODO: Integrate OpenAI Check
        pass
