from sqlalchemy import create_engine
from sqlalchemy.orm import declarative_base, sessionmaker
from app.core.config import settings

engine = create_engine(
    settings.DATABASE_URL,
    pool_pre_ping=True,       # Verify connection is alive before using
    pool_size=10,             # Connection pool size
    max_overflow=20           # Extra connections when pool is full
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# All models inherit from this
Base = declarative_base()
