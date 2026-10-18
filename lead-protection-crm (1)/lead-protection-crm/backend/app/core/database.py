import threading
from sqlalchemy import create_engine
from sqlalchemy.orm import declarative_base, sessionmaker
from app.core.config import settings

_thread_local = threading.local()

def set_current_db_session(session):
    _thread_local.session = session

def get_current_db_session():
    return getattr(_thread_local, "session", None)

db_url = settings.DATABASE_URL

# Handle Heroku/Render/Neon postgres:// to postgresql://
if db_url.startswith("postgres://"):
    db_url = db_url.replace("postgres://", "postgresql://", 1)

connect_args = {}
if db_url.startswith("sqlite"):
    connect_args = {"check_same_thread": False}

engine = create_engine(
    db_url,
    connect_args=connect_args,
    pool_pre_ping=True
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()

def get_db():
    db = SessionLocal()
    set_current_db_session(db)
    try:
        yield db
    finally:
        set_current_db_session(None)
        db.close()
