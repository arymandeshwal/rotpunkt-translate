from datetime import UTC, datetime, timedelta

import bcrypt
import jwt

from app.config import get_settings


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """
    Verify a plain password against a hashed password using bcrypt.

    Args:
        plain_password: The plaintext password provided by the user.
        hashed_password: The bcrypt hashed password stored in the database.

    Returns:
        True if the password matches the hash, False otherwise.
    """
    return bcrypt.checkpw(plain_password.encode("utf-8"), hashed_password.encode("utf-8"))


def get_password_hash(password: str) -> str:
    """
    Generate a bcrypt hash from a plain text password.

    Args:
        password: The plaintext password to hash.

    Returns:
        A string representing the bcrypt hash.
    """
    salt = bcrypt.gensalt()
    return bcrypt.hashpw(password.encode("utf-8"), salt).decode("utf-8")


def create_access_token(data: dict) -> str:
    """
    Create a JSON Web Token (JWT) for user authentication.

    Args:
        data: A dictionary containing the payload to encode in the token (e.g., 'sub', 'role').

    Returns:
        A signed JWT string encoded using the application's secret key.
    """
    settings = get_settings()
    to_encode = data.copy()
    expire = datetime.now(UTC) + timedelta(minutes=settings.access_token_expire_minutes)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, settings.secret_key, algorithm="HS256")
    return encoded_jwt
