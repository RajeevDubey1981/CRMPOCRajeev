"""The Parts database: a fourth, separate database (after the CRM, Sales and Marketing). It never shares a table, a
join or a foreign key with the others. They are linked only by reference numbers (a CRM user id, an item code, a
service/installation request number, a Queries thread id) and by calls made through the application. Parts is
switched off while PARTS_DATABASE_URL is empty."""

from __future__ import annotations

import logging

from fastapi import HTTPException, status
from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, sessionmaker

from app.config import settings


class PartsBase(DeclarativeBase):
    pass


_state: dict = {"engine": None, "factory": None}


def _build():
    url = (settings.parts_database_url or "").strip()
    if not url:
        return None, None
    kwargs = {"connect_args": {"check_same_thread": False}} if url.startswith("sqlite") else {}
    try:
        engine = create_engine(url, pool_pre_ping=True, future=True, **kwargs)
    except Exception as exc:  # a wrong driver or address must never stop the CRM from starting: Parts just stays off
        logging.getLogger(__name__).error("Parts database not usable, Parts stays off: %s", exc.__class__.__name__)
        return None, None
    return engine, sessionmaker(bind=engine, autoflush=False, autocommit=False, future=True)


_state["engine"], _state["factory"] = _build()


def use_factory(factory, engine=None) -> None:
    """Point Parts at another database (used by the tests)."""
    _state["factory"] = factory
    _state["engine"] = engine


def parts_enabled() -> bool:
    return _state["factory"] is not None


def parts_engine():
    return _state["engine"]


def new_parts_session():
    factory = _state["factory"]
    if factory is None:
        raise RuntimeError("The Parts database is not set up")
    return factory()


def get_parts_db():
    factory = _state["factory"]
    if factory is None:
        raise HTTPException(status.HTTP_503_SERVICE_UNAVAILABLE, "The Parts database is not set up yet")
    db = factory()
    try:
        yield db
    finally:
        db.close()
