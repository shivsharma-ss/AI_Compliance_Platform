from pydantic import BaseModel
from typing import Optional, List, Any
import datetime

class PromptRequestCreate(BaseModel):
    prompt_text: str
    intended_use: str
    context: Optional[str] = None

class PromptEvaluationResult(BaseModel):
    decision: str # ACCEPT, DECLINE
    reason_summary: str
    triggered_rules: List[int]

class PromptRequestResponse(BaseModel):
    id: int
    user_id: int
    prompt_text: str
    intended_use: str
    decision: Optional[str]
    reason_summary: Optional[str]
    created_at: datetime.datetime
    
    class Config:
        from_attributes = True
