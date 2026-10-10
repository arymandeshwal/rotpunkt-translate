from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.dependencies import get_current_user, require_role
from app.db import get_session
from app.models.user import Role, User
from app.schemas.user import UserCreate, UserResponse
from app.services.auth import get_password_hash

router = APIRouter(prefix="/users", tags=["users"])


@router.get("/me", response_model=UserResponse)
async def read_users_me(current_user: Annotated[User, Depends(get_current_user)]) -> User:
    """
    Get the currently authenticated user's profile.

    Args:
        current_user: The authenticated User object injected by the dependency.

    Returns:
        The current User object.
    """
    return current_user


@router.get("", response_model=list[UserResponse])
async def read_users(
    db_session: Annotated[AsyncSession, Depends(get_session)],
    current_user: Annotated[User, Depends(require_role([Role.ADMIN]))],
) -> list[User]:
    """
    List all users in the system. Only accessible by administrators.

    Args:
        db_session: The active asynchronous database session.
        current_user: The authenticated admin User object injected by the dependency.

    Returns:
        A list of User objects.
    """
    result = await db_session.execute(select(User))
    return list(result.scalars().all())


@router.post("", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
async def create_user(
    user_in: UserCreate,
    db_session: Annotated[AsyncSession, Depends(get_session)],
    current_user: Annotated[User, Depends(require_role([Role.ADMIN]))],
) -> User:
    """
    Create a new user. Only accessible by administrators.

    Args:
        user_in: The UserCreate schema containing the new user's details.
        db_session: The active asynchronous database session.
        current_user: The authenticated admin User object injected by the dependency.

    Returns:
        The newly created User object.

    Raises:
        HTTPException: 400 if the email is already registered.
    """
    # Check if user exists
    result = await db_session.execute(select(User).where(User.email == user_in.email))
    if result.scalars().first():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="Email already registered"
        )

    hashed_password = get_password_hash(user_in.password)
    new_user = User(email=user_in.email, hashed_password=hashed_password, role=user_in.role)

    db_session.add(new_user)
    await db_session.commit()
    await db_session.refresh(new_user)
    return new_user
