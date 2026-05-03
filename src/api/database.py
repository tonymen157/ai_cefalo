from sqlalchemy import create_engine, Column, String, Boolean, DateTime, Float, Text, PrimaryKeyConstraint, func, text
from sqlalchemy.orm import sessionmaker, scoped_session, declarative_base
from datetime import datetime
import os


DATABASE_URL = os.getenv(
    "DATABASE_URL",
    "sqlite:///./aicefalo.db"
)

engine = create_engine(DATABASE_URL, pool_pre_ping=True)
SessionLocal = scoped_session(
    sessionmaker(autocommit=False, autoflush=False, bind=engine)
)
Base = declarative_base()


def init_db():
    """Initialize database - import models to register tables and migrate columns."""
    from src.api import models  # noqa: F401
    Base.metadata.create_all(bind=engine)

    # Migración: añadir columnas faltantes usando PRAGMA (SQLite)
    with engine.connect() as conn:
        # Verificar y añadir system_warnings a jobs si no existe
        existing_cols = [row[1] for row in conn.execute(text("PRAGMA table_info(jobs)")).fetchall()]
        if "system_warnings" not in existing_cols:
            conn.execute(text("ALTER TABLE jobs ADD COLUMN system_warnings TEXT"))
            conn.commit()


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
