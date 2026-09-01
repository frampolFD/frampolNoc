import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app import models  # noqa: F401  (registers all tables on Base.metadata)
from app.auth import get_current_user
from app.database import Base, get_db
from app.models import User, UserRole


@pytest.fixture()
def db_session():
    """A fresh in-memory SQLite database per test — fully isolated from the
    real dev database (app/frampol_noc.db)."""
    engine = create_engine("sqlite:///:memory:", connect_args={"check_same_thread": False})
    Base.metadata.create_all(engine)
    session_factory = sessionmaker(bind=engine)
    session = session_factory()
    try:
        yield session
    finally:
        session.close()
        engine.dispose()


@pytest.fixture()
def client():
    """A FastAPI TestClient wired to an isolated in-memory DB, authenticated
    as a fake admin user (auth dependency overridden). Lifespan is
    intentionally not triggered (no `with` block), so the real background
    worker never starts against the real dev database during tests."""
    # StaticPool: TestClient dispatches requests on a different thread than
    # this fixture runs on, and SQLite's default thread-local pooling would
    # hand that thread a brand new (table-less) :memory: database. StaticPool
    # forces every thread onto the same single connection.
    engine = create_engine("sqlite:///:memory:", connect_args={"check_same_thread": False}, poolclass=StaticPool)
    Base.metadata.create_all(engine)
    session_factory = sessionmaker(bind=engine)
    session = session_factory()

    fake_user = User(id=1, name="Test Admin", email="test@example.com", role=UserRole.admin, password_hash="x")
    session.add(fake_user)
    session.commit()

    from app.main import app  # imported lazily so app startup doesn't happen at collection time

    def override_get_db():
        yield session

    def override_get_current_user():
        return fake_user

    app.dependency_overrides[get_db] = override_get_db
    app.dependency_overrides[get_current_user] = override_get_current_user

    test_client = TestClient(app)
    try:
        yield test_client
    finally:
        app.dependency_overrides.clear()
        session.close()
        engine.dispose()
