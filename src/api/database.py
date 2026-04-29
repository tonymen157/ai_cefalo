from sqlalchemy import create_engine, Column, String, Boolean, DateTime, Float, Text, PrimaryKeyConstraint, func
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
    """Initialize database - import models to register tables."""
    from src.api import models  # noqa: F401
    Base.metadata.create_all(bind=engine)


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
