from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from typing import List

from db.session import get_db
from models.user import User
from models.prompt import PromptRequest
from schemas.prompt import PromptRequestCreate, PromptRequestResponse
from services.rule_engine import RuleEngine
from core.security import verify_password
from core.config import settings
from jose import jwt, JWTError
from fastapi.security import OAuth2PasswordBearer

router = APIRouter()
oauth2_scheme = OAuth2PasswordBearer(tokenUrl=f"{settings.API_V1_STR}/auth/login")

async def get_current_user(token: str = Depends(oauth2_scheme), db: AsyncSession = Depends(get_db)):
    credentials_exception = HTTPException(
        status_code=401,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
        user_id: str = payload.get("sub")
        if user_id is None:
            raise credentials_exception
    except JWTError:
        raise credentials_exception
    
    result = await db.execute(select(User).where(User.id == int(user_id)))
    user = result.scalars().first()
    if user is None:
        raise credentials_exception
    return user

@router.post("/evaluate", response_model=PromptRequestResponse)
async def evaluate_prompt(
    request_in: PromptRequestCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    # 1. Evaluate
    engine = RuleEngine(db)
    # Convert schema to temp object or just use fields
    # We need a PromptRequest object but don't save it yet until we get result? 
    # Actually, we save request first + result.
    
    prompt_request = PromptRequest(
        user_id=current_user.id,
        prompt_text=request_in.prompt_text,
        intended_use=request_in.intended_use,
        context=request_in.context
    )
    
    evaluation = await engine.evaluate(prompt_request)
    
    prompt_request.decision = evaluation["decision"]
    prompt_request.reason_summary = evaluation["reason_summary"]
    
    db.add(prompt_request)
    await db.commit()
    await db.refresh(prompt_request)
    
    return prompt_request

@router.get("/history", response_model=List[PromptRequestResponse])
async def get_history(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    # If admin, show all? MVP says users see own. Admin dashboard separate.
    # For now, just user's own history.
    result = await db.execute(select(PromptRequest).where(PromptRequest.user_id == current_user.id).order_by(PromptRequest.created_at.desc()))
    return result.scalars().all()
