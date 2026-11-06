from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
import os

DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./atm_banking.db")

engine = create_engine(
    DATABASE_URL,
    connect_args={"check_same_thread": False} if "sqlite" in DATABASE_URL else {},
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def init_db():
    """Create all tables."""
    import app.models  # noqa: F401  ensure models are registered
    Base.metadata.create_all(bind=engine)
    _migrate_sqlite()


def _migrate_sqlite():
    """
    Lazy migration for existing SQLite databases created before newer
    columns were added to a model. Adds any missing column via ALTER TABLE.
    """
    if not engine.url.get_backend_name().startswith("sqlite"):
        return
    from sqlalchemy import text

    candidates = {
        "applications": {
            "session_key": "VARCHAR(255)",
            "service_id": "VARCHAR(64) DEFAULT ''",
        },
    }
    with engine.connect() as conn:
        for table, columns in candidates.items():
            rows = conn.execute(text(f"PRAGMA table_info({table})")).fetchall()
            existing = {row[1] for row in rows}
            if not existing:
                continue  # table not created yet - create_all handled it
            for col, ddl in columns.items():
                if col not in existing:
                    conn.execute(text(f"ALTER TABLE {table} ADD COLUMN {col} {ddl}"))
        conn.commit()
