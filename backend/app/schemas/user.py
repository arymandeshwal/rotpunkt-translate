from pydantic import BaseModel, EmailStr, ConfigDict
import uuid
from app.models.user import Role

class UserBase(BaseModel):
    email: EmailStr
    role: Role = Role.TRANSLATOR

class UserCreate(UserBase):
    password: str

class UserResponse(UserBase):
    id: uuid.UUID
    is_active: bool

    model_config = ConfigDict(from_attributes=True)

class Token(BaseModel):
    access_token: str
    token_type: str
