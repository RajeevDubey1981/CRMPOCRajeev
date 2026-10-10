"""Shared set-up for the Sales tests: two separate SQLite databases (the CRM and Sales), users, roles and helpers."""
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
from app.models import Complaint, Permission, Role, User
from app.sales.db import SalesBase, get_sales_db, use_factory
from app.sales.models import SalesLead
from app.security import create_access_token, hash_password


def sqlite_engine():
    return create_engine("sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool)


class SalesTestBase(unittest.TestCase):
    def setUp(self):
        self.main_engine = sqlite_engine()
        self.sales_engine = sqlite_engine()
        Base.metadata.create_all(self.main_engine)
        SalesBase.metadata.create_all(self.sales_engine)
        self.MainSession = sessionmaker(bind=self.main_engine, autoflush=False, autocommit=False, future=True)
        self.SalesSession = sessionmaker(bind=self.sales_engine, autoflush=False, autocommit=False, future=True)
        use_factory(self.SalesSession, self.sales_engine)
        self.db = self.MainSession()
        self.sdb = self.SalesSession()

        def main_override():
            s = self.MainSession()
            try:
                yield s
            finally:
                s.close()

        def sales_override():
            s = self.SalesSession()
            try:
                yield s
            finally:
                s.close()

        app.dependency_overrides[get_db] = main_override
        app.dependency_overrides[get_sales_db] = sales_override
        self.client = TestClient(app)

        roles = {}
        for name in ("admin", "sub_admin", "sales", "sales_manager", "callcenter"):
            r = Role(name=name, description=name)
            self.db.add(r)
            self.db.flush()
            roles[name] = r
        for name in ("sales", "sales_manager"):
            self.db.add(Permission(role_id=roles[name].id, module="sales", can_view=True))
        self.admin = self._user("admin@t.com", "admin", "Admin")
        self.sub = self._user("sub@t.com", "sub_admin", "Sub Admin")
        self.amit = self._user("amit@t.com", "sales", "Amit Verma")
        self.pooja = self._user("pooja@t.com", "sales", "Pooja Singh")
        self.karan = self._user("karan@t.com", "sales_manager", "Karan Malhotra")
        self.cc = self._user("cc@t.com", "callcenter", "Call Centre")
        self.db.commit()
        # profiles: Amit handles retail and spare in UP and Delhi, Pooja handles gem and tender in Rajasthan
        self.client.get("/api/sales/team", headers=self.h(self.admin))
        self.put(f"/api/sales/team/{self.amit.id}/profile", {"types_handled": "retail,spare", "areas": "Uttar Pradesh,Delhi", "pincode": "201301", "state": "Uttar Pradesh", "district": "Gautam Buddha Nagar"}, self.admin)
        self.put(f"/api/sales/team/{self.pooja.id}/profile", {"types_handled": "gem,tender", "areas": "Rajasthan,Gujarat"}, self.admin)

    def tearDown(self):
        use_factory(None, None)
        app.dependency_overrides.clear()
        self.db.close()
        self.sdb.close()

    # helpers
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

    def complaint(self, no, name, phone, text, state="Uttar Pradesh", qtype="Sales"):
        c = Complaint(comp_no=no, customer_name=name, customer_mobile=phone, problem_description=text, query_type=qtype, state=state, district="Noida", source="public", status="Pending")
        self.db.add(c)
        self.db.commit()
        return c

    def sync(self, who=None, **body):
        r = self.post("/api/sales/sync", body, who or self.karan)
        self.assertEqual(r.status_code, 200, r.text)
        return r.json()

    def lead_row(self, lead_id) -> SalesLead:
        self.sdb.expire_all()
        return self.sdb.get(SalesLead, lead_id)

    def new_lead(self, **kw):
        body = {"name": "Meena Traders", "phone": "99110 55667", "item": "Deep freezer 300 L x 15", "place": "Noida", "state": "Uttar Pradesh", **kw}
        r = self.post("/api/sales/leads", body, self.karan)
        self.assertEqual(r.status_code, 201, r.text)
        return r.json()["lead"]
