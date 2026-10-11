"""The Marketing database: a third, separate database (after the CRM and Sales). It never shares a table, a join or a
foreign key with the others. They are linked only by reference numbers (a CRM user id, a Sales lead id) and by calls
made through the application. Marketing is switched off while MARKETING_DATABASE_URL is empty."""

from __future__ import annotations

import logging

from fastapi import HTTPException, status
from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, sessionmaker

from app.config import settings


class MarketingBase(DeclarativeBase):
    pass


_state: dict = {"engine": None, "factory": None}


def _build():
    url = (settings.marketing_database_url or "").strip()
    if not url:
        return None, None
    kwargs = {"connect_args": {"check_same_thread": False}} if url.startswith("sqlite") else {}
    try:
        engine = create_engine(url, pool_pre_ping=True, future=True, **kwargs)
    except Exception as exc:  # a wrong driver or address must never stop the CRM from starting: Marketing just stays off
        logging.getLogger(__name__).error("Marketing database not usable, Marketing stays off: %s", exc.__class__.__name__)
        return None, None
    return engine, sessionmaker(bind=engine, autoflush=False, autocommit=False, future=True)


_state["engine"], _state["factory"] = _build()


def use_factory(factory, engine=None) -> None:
    """Point Marketing at another database (used by the tests)."""
    _state["factory"] = factory
    _state["engine"] = engine


def marketing_enabled() -> bool:
    return _state["factory"] is not None


def marketing_engine():
    return _state["engine"]


def new_marketing_session():
    factory = _state["factory"]
    if factory is None:
        raise RuntimeError("The Marketing database is not set up")
    return factory()


def get_marketing_db():
    factory = _state["factory"]
    if factory is None:
        raise HTTPException(status.HTTP_503_SERVICE_UNAVAILABLE, "The Marketing database is not set up yet")
    db = factory()
    try:
        yield db
    finally:
        db.close()
