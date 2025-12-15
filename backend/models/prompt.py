from sqlalchemy import Column, Integer, String, DateTime, JSON, ForeignKey, Text
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from models.base import Base

class PromptRequest(Base):
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("user.id"), nullable=False, index=True)
    prompt_text = Column(Text, nullable=False)
    intended_use = Column(String, nullable=False)
    context = Column(Text, nullable=True)
    decision = Column(String, nullable=True) # ACCEPT, DECLINE
    reason_summary = Column(String, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    # Relationships
    user = relationship("User", backref="requests")
    evaluation = relationship("PromptEvaluation", uselist=False, back_populates="request")

class PromptEvaluation(Base):
    id = Column(Integer, primary_key=True, index=True)
    request_id = Column(Integer, ForeignKey("promptrequest.id"), unique=True, nullable=False)
    llm_model = Column(String, nullable=True)
    llm_status = Column(String, nullable=True) # SUCCESS, FAILED
    llm_latency_ms = Column(Integer, nullable=True)
    classification_json = Column(JSON, nullable=True)
    triggered_rules_json = Column(JSON, nullable=True)
    trace_json = Column(JSON, nullable=True)
    
    request = relationship("PromptRequest", back_populates="evaluation")
