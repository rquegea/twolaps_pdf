"""
Database Connection Management
Gestión de sesiones y conexión con PostgreSQL
"""

import os
from contextlib import contextmanager
from typing import Generator
from dotenv import load_dotenv
from sqlalchemy import create_engine, event, text
from sqlalchemy.orm import sessionmaker, Session
from sqlalchemy.pool import QueuePool

from src.database.models import Base

# Load environment variables
load_dotenv()

# Database URL from environment
DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://localhost:5432/twolaps")

# Create engine with connection pooling
engine = create_engine(
    DATABASE_URL,
    poolclass=QueuePool,
    pool_size=5,
    max_overflow=10,
    pool_timeout=30,
    pool_recycle=3600,
    echo=False,  # Set to True for SQL query logging
)

# Session factory
SessionLocal = sessionmaker(
    autocommit=False,
    autoflush=False,
    bind=engine
)


def get_engine():
    """Get the SQLAlchemy engine instance"""
    return engine


@contextmanager
def get_session() -> Generator[Session, None, None]:
    """
    Context manager for database sessions
    
    Usage:
        with get_session() as session:
            result = session.query(Mercado).all()
    """
    session = SessionLocal()
    try:
        yield session
        session.commit()
    except Exception as e:
        session.rollback()
        raise e
    finally:
        session.close()


def init_db():
    """
    Initialize database - Create all tables
    Solo crea tablas si no existen
    """
    Base.metadata.create_all(bind=engine)
    print("✓ Database initialized successfully")


def drop_all_tables():
    """
    Drop all tables - USE WITH CAUTION
    Solo para desarrollo/testing
    """
    Base.metadata.drop_all(bind=engine)
    print("✓ All tables dropped")


def reset_db():
    """
    Reset database - Drop and recreate all tables
    Solo para desarrollo/testing
    """
    drop_all_tables()
    init_db()
    print("✓ Database reset completed")


# Event listener para habilitar pgvector en cada conexión
@event.listens_for(engine, "connect")
def connect(dbapi_connection, connection_record):
    """Enable pgvector extension on connection"""
    cursor = dbapi_connection.cursor()
    try:
        cursor.execute("CREATE EXTENSION IF NOT EXISTS vector")
        dbapi_connection.commit()
    except Exception:
        # Extension might already exist or user lacks permissions
        pass
    finally:
        cursor.close()


def test_connection():
    """
    Test database connection
    Returns True if connection is successful
    """
    try:
        with get_session() as session:
            session.execute(text("SELECT 1"))
        print("✓ Database connection successful")
        return True
    except Exception as e:
        print(f"✗ Database connection failed: {e}")
        return False


# Utility function to get a session directly (not as context manager)
def create_session() -> Session:
    """
    Create a new session - Remember to close it manually
    
    Usage:
        session = create_session()
        try:
            # ... do work ...
            session.commit()
        finally:
            session.close()
    """
    return SessionLocal()


if __name__ == "__main__":
    # Test when run directly
    print("Testing database connection...")
    test_connection()

