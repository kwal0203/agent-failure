from dotenv import load_dotenv
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session
from collections.abc import Generator

from apps.control_plane.src.infrastructure.config.settings import get_database_url


load_dotenv()

engine = create_engine(
    url=get_database_url(),
    future=True,
    pool_pre_ping=True,
    pool_recycle=300,
)
SessionFactory: sessionmaker[Session] = sessionmaker(
    bind=engine,
    class_=Session,
    autocommit=False,
    autoflush=False,
    expire_on_commit=False,
)


def get_db_session() -> Generator[Session, None, None]:
    db = SessionFactory()
    try:
        yield db
    finally:
        db.close()
