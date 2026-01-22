from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from jose import jwt, JWTError
import logging

from db.session import get_db
from models.user import User
from core.config import settings

logger = logging.getLogger(__name__)

oauth2_scheme = OAuth2PasswordBearer(tokenUrl=f"{settings.API_V1_STR}/auth/login")

async def get_current_user(token: str = Depends(oauth2_scheme), db: AsyncSession = Depends(get_db)):
    """
    Authenticate a request using a bearer JWT and return the corresponding User.
    
    Validates the provided JWT, extracts the `sub` claim as the user id, and looks up that user in the database. Raises an HTTP 401 if the token is invalid, the `sub` claim is missing, or no matching user is found.
    
    Parameters:
        token (str): Bearer token extracted from the Authorization header.
        db (AsyncSession): Asynchronous database session.
    
    Returns:
        User: The authenticated user instance.
    
    Raises:
        HTTPException: 401 Unauthorized when credentials are missing, invalid, or no user matches the token.
    """
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
        user_id = payload.get("sub")
        if user_id is None:
            raise credentials_exception
        try:
            user_id_int = int(user_id)
        except (TypeError, ValueError) as exc:
            logger.warning("Invalid user id in token payload", extra={"user_id": user_id})
            raise credentials_exception from exc
    except JWTError as exc:
        raise credentials_exception from exc
    
    result = await db.execute(select(User).where(User.id == user_id_int))
    user = result.scalars().first()
    if user is None:
        raise credentials_exception
    if not user.is_active:
        raise credentials_exception
    return user
