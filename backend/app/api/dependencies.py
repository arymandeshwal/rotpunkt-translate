from typing import Annotated

import jwt
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import get_settings
from app.db import get_session
from app.models.user import Role, User

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="api/auth/token")


async def get_current_user(
    token: Annotated[str, Depends(oauth2_scheme)], db: Annotated[AsyncSession, Depends(get_session)]
) -> User:
    """
    FastAPI dependency to retrieve the current user from the Authorization header JWT.

    Args:
        token: The encoded JWT provided via the OAuth2PasswordBearer scheme.
        db: The active asynchronous database session.

    Returns:
        The authenticated User object from the database.

    Raises:
        HTTPException: 401 if the token is invalid, expired, or the user does not exist.
        HTTPException: 400 if the user account is inactive.
    """
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    settings = get_settings()
    try:
        payload = jwt.decode(token, settings.secret_key, algorithms=["HS256"])
        email: str | None = payload.get("sub")
        if email is None:
            raise credentials_exception
    except jwt.InvalidTokenError:
        raise credentials_exception

    result = await db.execute(select(User).where(User.email == email))
    user = result.scalars().first()
    if user is None:
        raise credentials_exception
    if not user.is_active:
        raise HTTPException(status_code=400, detail="Inactive user")

    return user


def require_role(allowed_roles: list[Role]):
    """
    FastAPI dependency factory to restrict endpoint access by user role.

    Args:
        allowed_roles: A list of Role enums permitted to access the endpoint.

    Returns:
        An asynchronous dependency function that checks the current user's role.

    Raises:
        HTTPException: 403 if the authenticated user's role is not in the allowed_roles list.
    """

    async def role_checker(current_user: Annotated[User, Depends(get_current_user)]) -> User:
        if current_user.role not in allowed_roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN, detail="Not enough privileges"
            )
        return current_user

    return role_checker
