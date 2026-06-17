from sqlalchemy import create_engine, event
from sqlalchemy.orm import declarative_base, sessionmaker
from app.core.config import settings

engine = create_engine(
    settings.DATABASE_URL,
    pool_pre_ping=True,       # Verify connection is alive before using
    pool_size=10,             # Connection pool size
    max_overflow=20           # Extra connections when pool is full
)


@event.listens_for(engine, "connect")
def set_search_path(dbapi_connection, connection_record):
    set_public_search_path(dbapi_connection)


@event.listens_for(engine, "checkout")
def reset_search_path(dbapi_connection, connection_record, connection_proxy):
    set_public_search_path(dbapi_connection)


def set_public_search_path(dbapi_connection):
    cursor = dbapi_connection.cursor()
    try:
        cursor.execute("SET search_path TO public")
    finally:
        cursor.close()


SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# All models inherit from this
Base = declarative_base()
