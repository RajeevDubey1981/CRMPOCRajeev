"""Shared set-up for the Parts tests: two separate SQLite databases (the CRM and Parts), users, roles and helpers."""
from __future__ import annotations

import os
import sys
import unittest
from pathlib import Path

os.environ.setdefault("MYSQL_DATABASE_URL", "sqlite://")
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.database import Base, get_db
from app.main import app
from app.models import Role, User
from app.parts.db import PartsBase, get_parts_db, use_factory
from app.security import create_access_token, hash_password


def sqlite_engine():
    return create_engine("sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool)


class PartsTestBase(unittest.TestCase):
    def setUp(self):
        self.main_engine = sqlite_engine()
        self.parts_engine = sqlite_engine()
        Base.metadata.create_all(self.main_engine)
        PartsBase.metadata.create_all(self.parts_engine)
        self.MainSession = sessionmaker(bind=self.main_engine, autoflush=False, autocommit=False, future=True)
        self.PartsSession = sessionmaker(bind=self.parts_engine, autoflush=False, autocommit=False, future=True)
        use_factory(self.PartsSession, self.parts_engine)
        self.db = self.MainSession()
        self.pdb = self.PartsSession()

        def main_override():
            s = self.MainSession()
            try:
                yield s
            finally:
                s.close()

        def parts_override():
            s = self.PartsSession()
            try:
                yield s
            finally:
                s.close()

        app.dependency_overrides[get_db] = main_override
        app.dependency_overrides[get_parts_db] = parts_override
        self.client = TestClient(app)

        for name in ("admin", "sub_admin", "service_manager", "engineer", "sales"):
            self.db.add(Role(name=name, description=name))
        self.db.flush()
        self.admin = self._user("admin@t.com", "admin", "Admin")
        self.sub = self._user("sub@t.com", "sub_admin", "Sub Admin")
        self.svm = self._user("svm@t.com", "service_manager", "Neha Gupta")
        self.eng = self._user("eng@t.com", "engineer", "Amit Verma")
        self.sales = self._user("sales@t.com", "sales", "Karan Malhotra")
        self.db.commit()

    def tearDown(self):
        use_factory(None, None)
        app.dependency_overrides.clear()
        self.db.close()
        self.pdb.close()

    def _user(self, email, role, name):
        u = User(name=name, email=email, password_hash=hash_password("pw123456"), role=role, is_active=True)
        self.db.add(u)
        self.db.flush()
        return u

    def h(self, user):
        return {"Authorization": f"Bearer {create_access_token(subject=str(user.id), extra_claims={'role': user.role})}"}

    def get(self, url, who, **kw):
        return self.client.get(url, headers=self.h(who), **kw)

    def post(self, url, body, who):
        return self.client.post(url, json=body, headers=self.h(who))

    def put(self, url, body, who):
        return self.client.put(url, json=body, headers=self.h(who))
