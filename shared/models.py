import uuid
from datetime import datetime, timezone

from sqlalchemy import Column, DateTime, Float, ForeignKey, Integer, String, Text
from sqlalchemy.orm import declarative_base, relationship

Base = declarative_base()


class User(Base):
    __tablename__ = "users"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    telegram_id = Column(Integer, unique=True, nullable=False)
    username = Column(String(100), nullable=True)
    first_name = Column(String(100), nullable=True)
    role = Column(String(20), nullable=False, default="user")
    quota_used = Column(Integer, nullable=False, default=0)
    quota_limit = Column(Integer, nullable=False, default=1_000_000)
    quota_reset_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, nullable=False, default=lambda: datetime.now(timezone.utc))
    last_login_at = Column(DateTime, nullable=True)

    tasks = relationship("Task", back_populates="user")


class Task(Base):
    __tablename__ = "tasks"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id = Column(String(36), ForeignKey("users.id"), nullable=True)
    status = Column(String(20), nullable=False, default="pending")
    progress = Column(Float, nullable=False, default=0.0)
    error_msg = Column(Text, nullable=True)
    chars_translated = Column(Integer, nullable=False, default=0)
    original_filename = Column(String(255), nullable=True)
    result_filename = Column(String(255), nullable=True)
    page_range = Column(String(255), nullable=True)
    created_at = Column(DateTime, nullable=False, default=lambda: datetime.now(timezone.utc))
    updated_at = Column(DateTime, nullable=False, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))
    completed_at = Column(DateTime, nullable=True)

    user = relationship("User", back_populates="tasks")
