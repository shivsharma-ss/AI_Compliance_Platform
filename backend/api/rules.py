from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from typing import List

from db.session import get_db
from models.user import User
from models.rule import Rule
from schemas.rule import RuleCreate, RuleResponse
from api.deps import get_current_user

router = APIRouter()

# Dependency to check if user is admin
def get_current_admin(current_user: User = Depends(get_current_user)):
    if current_user.role != "admin":
        raise HTTPException(status_code=403, detail="Not authorized")
    return current_user

@router.post("/", response_model=RuleResponse)
async def create_rule(
    rule_in: RuleCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_admin)
):
    # Check uniqueness
    result = await db.execute(select(Rule).where(Rule.name == rule_in.name))
    if result.scalars().first():
        raise HTTPException(status_code=400, detail="Rule with this name already exists")
    
    rule = Rule(
        name=rule_in.name,
        description=rule_in.description,
        type=rule_in.type,
        payload_json=rule_in.payload_json,
        severity=rule_in.severity,
        is_active=rule_in.is_active
    )
    db.add(rule)
    await db.commit()
    await db.refresh(rule)
    return rule

@router.get("/", response_model=List[RuleResponse])
async def read_rules(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_admin)
):
    result = await db.execute(select(Rule))
    return result.scalars().all()
