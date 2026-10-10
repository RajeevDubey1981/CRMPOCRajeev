"""The Sales database: a second, separate database. It never shares a table, a join or a foreign key with the CRM
database. The two are linked only by reference numbers (a CRM user id, an enquiry number IDC_... / PR-...) and by
calls made through the application."""

from __future__ import annotations

from fastapi import HTTPException, status
from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, sessionmaker

from app.config import settings


class SalesBase(DeclarativeBase):
    pass


_state: dict = {"engine": None, "factory": None}


def _build():
    url = (settings.sales_database_url or "").strip()
    if not url:
        return None, None
    kwargs = {"connect_args": {"check_same_thread": False}} if url.startswith("sqlite") else {}
    engine = create_engine(url, pool_pre_ping=True, future=True, **kwargs)
    return engine, sessionmaker(bind=engine, autoflush=False, autocommit=False, future=True)


_state["engine"], _state["factory"] = _build()


def use_factory(factory, engine=None) -> None:
    """Point Sales at another database (used by the tests)."""
    _state["factory"] = factory
    _state["engine"] = engine


def sales_enabled() -> bool:
    return _state["factory"] is not None


def sales_engine():
    return _state["engine"]


def new_sales_session():
    factory = _state["factory"]
    if factory is None:
        raise RuntimeError("The Sales database is not set up")
    return factory()


def get_sales_db():
    factory = _state["factory"]
    if factory is None:
        raise HTTPException(status.HTTP_503_SERVICE_UNAVAILABLE, "The Sales database is not set up yet")
    db = factory()
    try:
        yield db
    finally:
        db.close()
