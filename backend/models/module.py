from sqlalchemy import Column, Integer, String, Boolean, DateTime, func
from .base import Base

class Module(Base):
    __tablename__ = "module"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False, unique=True)
    display_name = Column(String, nullable=True)
    enabled = Column(Boolean, default=True, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
