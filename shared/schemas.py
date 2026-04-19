from pydantic import BaseModel
from typing import Optional


class TelegramAuthData(BaseModel):
    id: int
    username: Optional[str] = None
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    photo_url: Optional[str] = None
    auth_date: int
    hash: str


class AuthResponse(BaseModel):
    access_token: str
    user: dict


class UserResponse(BaseModel):
    id: str
    telegram_id: int
    username: Optional[str]
    first_name: Optional[str]
    role: str
    quota_used: int
    quota_limit: int
    created_at: str


class AdminUserResponse(BaseModel):
    id: str
    telegram_id: int
    username: Optional[str]
    first_name: Optional[str]
    role: str
    quota_used: int
    quota_limit: int
    created_at: str
    last_login_at: Optional[str]


class QuotaUpdate(BaseModel):
    quota_limit: int
