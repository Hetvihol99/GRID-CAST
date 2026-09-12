"""
SQLAlchemy database connection setup.

- Uses SQLAlchemy 2.0 async-compatible session factory.
- Connection string comes from settings (never hardcoded).
- get_db() is a FastAPI dependency injected into route handlers.
"""

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, DeclarativeBase
from app.core.config import settings
from app.core.logging_config import get_logger

logger = get_logger(__name__)

# ── Engine ────────────────────────────────────────────────────────────────────
is_sqlite = settings.DATABASE_URL.startswith("sqlite")
engine_kwargs = {"echo": settings.DEBUG}

if is_sqlite:
    engine_kwargs["connect_args"] = {"check_same_thread": False}
else:
    engine_kwargs["pool_pre_ping"] = True
    engine_kwargs["pool_size"] = 10
    engine_kwargs["max_overflow"] = 20

engine = create_engine(settings.DATABASE_URL, **engine_kwargs)

# ── Session factory ───────────────────────────────────────────────────────────
SessionLocal = sessionmaker(
    autocommit=False,
    autoflush=False,
    bind=engine,
)


# ── Base class for all ORM models ─────────────────────────────────────────────
class Base(DeclarativeBase):
    pass


# ── FastAPI dependency ────────────────────────────────────────────────────────
def get_db():
    """
    Yield a database session and ensure it is closed after the request.

    Usage in route handlers:
        @router.get("/plants")
        def get_plants(db: Session = Depends(get_db)):
            ...
    """
    db = SessionLocal()
    try:
        yield db
    except Exception as exc:
        logger.error(f"Database session error: {exc}")
        db.rollback()
        raise
    finally:
        db.close()


def create_tables() -> None:
    """
    Create all tables defined in ORM models.
    Called once at application startup (not on every request).
    For production migrations, use Alembic instead.
    """
    # Import models so SQLAlchemy registers them before create_all
    from app.database import models  # noqa: F401
    logger.info("Creating database tables...")
    Base.metadata.create_all(bind=engine)
    logger.info("Database tables ready.")
