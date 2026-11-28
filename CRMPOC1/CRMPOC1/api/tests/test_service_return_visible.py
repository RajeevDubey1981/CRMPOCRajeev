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
from app.models.pending_action import UserPendingAction
from app.models.service import ServiceRequest
from app.security import create_access_token, hash_password
from app.seed import seed_roles


class ReturnToManagerTests(unittest.TestCase):
    def setUp(self):
        engine = create_engine("sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool)
        Base.metadata.create_all(engine)
        self.Session = sessionmaker(bind=engine, expire_on_commit=False)
        self.db = self.Session()
        seed_roles(self.db)
        self.admin = User(name="Admin", email="a@x.com", password_hash=hash_password("x"), role="admin", is_active=True)
        self.manager = User(name="Manu Manager", email="m@x.com", password_hash=hash_password("x"), role="service_manager", is_active=True)
        self.desk = User(name="Sunil Service", email="s@x.com", password_hash=hash_password("x"), role="service", is_active=True)
        self.db.add_all([self.admin, self.manager, self.desk])
        self.db.commit()
        sr = ServiceRequest(request_no="SRV_1", status="Assigned", query_type="Service", customer_name="N", customer_mobile="9876543210",
                            problem_description="p", assigned_service_user_id=self.desk.id)
        self.db.add(sr)
        self.db.commit()
        self.sid = sr.id

        def override():
            s = self.Session()
            try:
                yield s
            finally:
                s.close()

        app.dependency_overrides[get_db] = override
        self.client = TestClient(app, raise_server_exceptions=False)

    def tearDown(self):
        app.dependency_overrides.clear()
        self.db.close()

    def h(self, u):
        return {"Authorization": f"Bearer {create_access_token(subject=str(u.id), extra_claims={'role': u.role})}"}

    def test_return_is_labelled_filtered_and_notified(self):
        r = self.client.post(f"/api/services/{self.sid}/return-to-service-manager", json={"remarks": "Customer not reachable"}, headers=self.h(self.desk))
        self.assertEqual(r.status_code, 200, r.text)
        rows = self.client.get("/api/services?returned=true", headers=self.h(self.admin)).json()["items"]
        self.assertEqual(len(rows), 1)
        self.assertEqual((rows[0]["returned_by_name"], rows[0]["returned_reason"]), ("Sunil Service", "Customer not reachable"))
        self.db.expire_all()
        s = self.Session()
        kinds = {(a.recipient_user_id, a.action_type) for a in s.query(UserPendingAction).all() if a.action_type == "returned_service"}
        s.close()
        self.assertIn((self.manager.id, "returned_service"), kinds)

    def test_not_returned_rows_have_no_label(self):
        rows = self.client.get("/api/services", headers=self.h(self.admin)).json()["items"]
        self.assertIsNone(rows[0]["returned_by_name"])
        self.assertEqual(self.client.get("/api/services?returned=true", headers=self.h(self.admin)).json()["items"], [])


if __name__ == "__main__":
    unittest.main()
