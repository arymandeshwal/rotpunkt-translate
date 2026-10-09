from typing import Annotated
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.db import get_session
from app.models.user import User, Role
from app.schemas.user import UserCreate, UserResponse
from app.services.auth import get_password_hash
from app.api.dependencies import get_current_user, require_role

router = APIRouter(prefix="/users", tags=["users"])

@router.get("/me", response_model=UserResponse)
async def read_users_me(
    current_user: Annotated[User, Depends(get_current_user)]
) -> User:
    return current_user

@router.get("", response_model=list[UserResponse])
async def read_users(
    db_session: Annotated[AsyncSession, Depends(get_session)],
    current_user: Annotated[User, Depends(require_role([Role.ADMIN]))]
) -> list[User]:
    result = await db_session.execute(select(User))
    return list(result.scalars().all())

@router.post("", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
async def create_user(
    user_in: UserCreate,
    db_session: Annotated[AsyncSession, Depends(get_session)],
    current_user: Annotated[User, Depends(require_role([Role.ADMIN]))]
) -> User:
    # Check if user exists
    result = await db_session.execute(select(User).where(User.email == user_in.email))
    if result.scalars().first():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email already registered"
        )
        
    hashed_password = get_password_hash(user_in.password)
    new_user = User(
        email=user_in.email,
        hashed_password=hashed_password,
        role=user_in.role
    )
    
    db_session.add(new_user)
    await db_session.commit()
    await db_session.refresh(new_user)
    return new_user
