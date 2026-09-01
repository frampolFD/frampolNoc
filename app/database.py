from datetime import timezone

from sqlalchemy import DateTime, create_engine
from sqlalchemy.orm import declarative_base, sessionmaker
from sqlalchemy.types import TypeDecorator

from app.config import settings

connect_args = {"check_same_thread": False} if settings.database_url.startswith("sqlite") else {}
engine = create_engine(settings.database_url, connect_args=connect_args)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()


class UTCDateTime(TypeDecorator):
    """DateTime(timezone=True) that survives SQLite.

    SQLite has no real timestamp-with-timezone type: SQLAlchemy's SQLite
    dialect writes our timezone-aware UTC datetimes as plain strings and
    reads them back naive (no tzinfo). That breaks both Python-side
    arithmetic against a fresh `datetime.now(timezone.utc)` and, just as
    importantly, API serialization — a naive datetime becomes a
    timezone-less ISO string in JSON, which browsers parse as *local* time
    per the JS spec, silently shifting every timestamp shown in the UI by
    the browser's UTC offset.

    Every datetime this app writes is already UTC, so re-attaching UTC
    tzinfo to whatever SQLite hands back is correct and lossless.
    """

    impl = DateTime(timezone=True)
    cache_ok = True

    def process_result_value(self, value, dialect):
        if value is not None and value.tzinfo is None:
            return value.replace(tzinfo=timezone.utc)
        return value


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
