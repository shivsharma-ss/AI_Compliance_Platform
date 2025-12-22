from pydantic import BaseModel
from typing import Optional

class ModuleResponse(BaseModel):
    name: str
    display_name: Optional[str]
    enabled: bool
    status: Optional[str] = None
    url: Optional[str] = None

    class Config:
        orm_mode = True

class ModuleUpdate(BaseModel):
    enabled: bool
