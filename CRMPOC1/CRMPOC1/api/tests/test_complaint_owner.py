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
from app.models import User
from app.models.complaint import Complaint
from app.models.service import ServiceRequest
from app.security import create_access_token, hash_password
from app.seed import seed_roles


class ComplaintOwnerTests(unittest.TestCase):
    """The Service Manager gives a complaint's service request to a service team member (its owner) from the complaint list."""

    def setUp(self):
        engine = create_engine("sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool)
        Base.metadata.create_all(engine)
        self.Session = sessionmaker(bind=engine, autoflush=False, autocommit=False, future=True)
        self.db = self.Session()
        seed_roles(self.db)
        self.manager = self._user("mgr@t.com", "service_manager")
        self.vikash = self._user("vikash@t.com", "service", "Vikash Bhati")
        self.kuldeep = self._user("kuldeep@t.com", "service", "Kuldeep Maurya")
        self.eng = self._user("eng@t.com", "engineer")
        c = Complaint(comp_no="IDC_1", customer_name="Central Bank", customer_mobile="9000000000", query_type="Service", status="Pending")
        self.db.add(c)
        self.db.flush()
        s = ServiceRequest(request_no="SRV_1", status="New", customer_name="Central Bank", customer_mobile="9000000000", complaint_id=c.id)
        self.db.add(s)
        self.db.commit()
        self.cid, self.sid = c.id, s.id

        def override():
            sess = self.Session()
            try:
                yield sess
            finally:
                sess.close()

        app.dependency_overrides[get_db] = override
        self.client = TestClient(app, raise_server_exceptions=False)

    def tearDown(self):
        app.dependency_overrides.clear()
        self.db.close()

    def _user(self, email, role, name=None):
        u = User(name=name or email.split("@")[0], email=email, password_hash=hash_password("pw123456"), role=role, is_active=True)
        self.db.add(u)
        self.db.flush()
        return u

    def h(self, user):
        return {"Authorization": f"Bearer {create_access_token(subject=str(user.id), extra_claims={'role': user.role})}"}

    def row(self, user):
        r = self.client.get("/api/complaints", headers=self.h(user))
        self.assertEqual(r.status_code, 200, r.text)
        return next(i for i in r.json()["items"] if i["id"] == self.cid)

    def test_the_manager_sees_the_service_team_and_a_complaint_without_an_owner(self):
        names = [u["name"] for u in self.client.get("/api/services/lookup/service-users", headers=self.h(self.manager)).json()]
        self.assertEqual(sorted(names), ["Kuldeep Maurya", "Vikash Bhati"])
        row = self.row(self.manager)
        self.assertEqual((row["service_request_id"], row["service_owner_id"], row["service_owner_name"]), (self.sid, None, None))

    def test_assigning_an_owner_shows_on_the_complaint_and_can_be_changed(self):
        r = self.client.post(f"/api/services/{self.sid}/assign-service-user", json={"service_user_id": self.vikash.id}, headers=self.h(self.manager))
        self.assertEqual(r.status_code, 200, r.text)
        row = self.row(self.manager)
        self.assertEqual((row["service_owner_id"], row["service_owner_name"]), (self.vikash.id, "Vikash Bhati"))
        self.client.post(f"/api/services/{self.sid}/assign-service-user", json={"service_user_id": self.kuldeep.id}, headers=self.h(self.manager))
        self.assertEqual(self.row(self.manager)["service_owner_name"], "Kuldeep Maurya")

    def test_others_get_no_team_list_and_cannot_assign(self):
        self.assertEqual(self.client.get("/api/services/lookup/service-users", headers=self.h(self.eng)).json(), [])
        r = self.client.post(f"/api/services/{self.sid}/assign-service-user", json={"service_user_id": self.vikash.id}, headers=self.h(self.eng))
        self.assertIn(r.status_code, (403, 404))


if __name__ == "__main__":
    unittest.main()
