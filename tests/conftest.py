import os
import sys
import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from shared.config import settings
from shared.database import engine, init_db, SessionLocal
from shared.models import Base, Task


@pytest.fixture(autouse=True)
def setup_db():
    init_db()
    yield
    # Cleanup: drop all tables after each test
    Base.metadata.drop_all(bind=engine)


@pytest.fixture
def db_session():
    session = SessionLocal()
    try:
        yield session
    finally:
        session.close()
