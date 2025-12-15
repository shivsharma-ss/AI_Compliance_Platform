from sqlalchemy import Boolean, Column, Integer, String, DateTime, JSON
from sqlalchemy.sql import func
from models.base import Base

class Rule(Base):
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, unique=True, index=True, nullable=False)
    description = Column(String)
    type = Column(String, nullable=False) # REGEX, KEYWORD, LLM
    payload_json = Column(JSON, nullable=False) # e.g. {"pattern": "bomb"}
    severity = Column(String, default="BLOCK") # BLOCK, WARN
    is_active = Column(Boolean, default=True)
    version = Column(Integer, default=1)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
