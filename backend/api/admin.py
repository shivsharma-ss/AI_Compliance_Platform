from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, case
from typing import List, Any

from db.session import get_db
from models.user import User
from models.prompt import PromptRequest
from schemas.prompt import PromptRequestResponse
from api.rules import get_current_admin

router = APIRouter()

@router.get("/users/stats")
async def get_users_stats(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_admin)
):
    """
    Returns list of users with their prompt statistics (total, accepted, declined).
    """
    # Group by User and count decisions
    # We want: User Info + Accepted Count + Declined Count
    
    # Subquery for stats
    stmt = select(
        PromptRequest.user_id,
        func.count(PromptRequest.id).label("total"),
        func.sum(case((PromptRequest.decision == "ACCEPT", 1), else_=0)).label("accepted_count"),
        func.sum(case((PromptRequest.decision == "DECLINE", 1), else_=0)).label("declined_count")
    ).group_by(PromptRequest.user_id).subquery()
    
    # Join with User table
    query = select(
        User.id, 
        User.email, 
        stmt.c.total, 
        stmt.c.accepted_count, 
        stmt.c.declined_count
    ).outerjoin(stmt, User.id == stmt.c.user_id).where(User.role != "admin")
    
    result = await db.execute(query)
    rows = result.all()
    
    stats = []
    for row in rows:
        stats.append({
            "id": row.id,
            "email": row.email,
            "total_prompts": row.total or 0,
            "accepted_count": row.accepted_count or 0,
            "declined_count": row.declined_count or 0
        })
    return stats

@router.get("/users/{user_id}/history", response_model=List[PromptRequestResponse])
async def get_user_history(
    user_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_admin)
):
    """
    Returns full prompt history for a specific user.
    """
    result = await db.execute(
        select(PromptRequest)
        .where(PromptRequest.user_id == user_id)
        .order_by(PromptRequest.created_at.desc())
    )
    return result.scalars().all()
