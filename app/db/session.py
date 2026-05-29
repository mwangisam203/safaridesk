from app.db.base import SessionLocal

def get_db():
    """
    FastAPI dependency — provides a database session to every route that needs it.
    Automatically closes the session when the request is done.
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()