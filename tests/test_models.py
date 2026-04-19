from shared.database import init_db, SessionLocal, engine
from shared.models import Base, Task


def test_init_db():
    init_db()
    inspector = __import__("sqlalchemy").inspect(engine)
    assert "tasks" in inspector.get_table_names()


def test_task_creation(db_session):
    task = Task(
        status="pending",
        original_filename="test.pdf",
    )
    db_session.add(task)
    db_session.commit()

    assert task.id is not None
    assert task.status == "pending"
    assert task.progress == 0.0
    assert task.chars_translated == 0


def test_task_update(db_session):
    task = Task(status="processing", progress=50.0)
    db_session.add(task)
    db_session.commit()

    task.status = "completed"
    task.progress = 100.0
    db_session.commit()

    fetched = db_session.query(Task).filter(Task.id == task.id).first()
    assert fetched.status == "completed"
    assert fetched.progress == 100.0
