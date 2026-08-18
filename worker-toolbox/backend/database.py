"""
数据库配置 — SQLAlchemy 引擎、会话工厂、依赖注入。
"""

from sqlalchemy import create_engine, event
from sqlalchemy.orm import sessionmaker, Session, declarative_base

from backend.config import config

engine = create_engine(
    config.db_url,
    connect_args={"check_same_thread": False} if "sqlite" in config.db_url else {},
    echo=False,
)


@event.listens_for(engine, "connect")
def _set_sqlite_pragma(dbapi_connection, connection_record):
    """开启 SQLite 外键约束（Agent 表级联删除用）。"""
    if "sqlite" in config.db_url:
        cursor = dbapi_connection.cursor()
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.close()

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()


def get_db():
    """FastAPI 依赖注入：每次请求提供独立的数据库会话。"""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
