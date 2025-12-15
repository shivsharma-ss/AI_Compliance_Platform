from pydantic import BaseModel
from typing import Optional, Dict, Any
from datetime import datetime

class RuleBase(BaseModel):
    name: str
    description: Optional[str] = None
    type: str # REGEX, KEYWORD, LLM
    payload_json: Dict[str, Any]
    severity: str = "BLOCK" # BLOCK, WARN
    is_active: bool = True

class RuleCreate(RuleBase):
    pass

class RuleUpdate(RuleBase):
    pass

class RuleResponse(RuleBase):
    id: int
    version: int
    updated_at: datetime
    
    class Config:
        from_attributes = True
