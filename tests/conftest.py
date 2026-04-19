import os
import sys
import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from shared.config import settings
from shared.database import engine, init_db, SessionLocal
from shared.models import Base, Task, User


@pytest.fixture(autouse=True)
def setup_db():
    init_db()
    yield
    Base.metadata.drop_all(bind=engine)


@pytest.fixture
def db_session():
    session = SessionLocal()
    try:
        yield session
    finally:
        session.close()


@pytest.fixture
def test_user(db_session):
    user = User(
        telegram_id=99999,
        username="testuser",
        first_name="Test",
        role="user",
        quota_limit=1_000_000,
        quota_used=0,
    )
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)
    yield user
    db_session.delete(user)
    db_session.commit()


@pytest.fixture
def admin_user(db_session):
    user = User(
        telegram_id=1,
        username="admin",
        first_name="Admin",
        role="admin",
        quota_limit=999_999_999,
        quota_used=0,
    )
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)
    yield user
    db_session.delete(user)
    db_session.commit()
