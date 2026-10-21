from __future__ import annotations

import os
import sys
import unittest
from pathlib import Path

os.environ.setdefault("MYSQL_DATABASE_URL", "sqlite://")
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from fastapi.testclient import TestClient
from sqlalchemy import create_engine, event, func, select
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.database import Base, get_db
from app.main import app
from app.models import User
from app.models.service import ServiceRequest, ServiceStatusLog
from app.models.shortage_claim import ShortageClaim
from app.security import create_access_token, hash_password
from app.seed import seed_roles


class DeleteServiceRequestTests(unittest.TestCase):
    """Admin and Sub Admin delete a service request. The database refuses to remove a request that still has history rows,
    so the history must go first (this crashed with a 500 on the live server)."""

    def setUp(self):
        engine = create_engine("sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool)

        @event.listens_for(engine, "connect")
        def _foreign_keys_on(conn, _record):  # the live MySQL enforces them; SQLite only when told to
            conn.execute("PRAGMA foreign_keys=ON")

        Base.metadata.create_all(engine)
        self.Session = sessionmaker(bind=engine, autoflush=False, autocommit=False, future=True)
        self.db = self.Session()
        seed_roles(self.db)
        self.admin = self._user("admin@t.com", "admin")
        self.sub = self._user("sub@t.com", "sub_admin")
        self.eng = self._user("eng@t.com", "engineer")
        self.db.commit()

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

    def _user(self, email, role):
        u = User(name=email.split("@")[0], email=email, password_hash=hash_password("pw123456"), role=role, is_active=True)
        self.db.add(u)
        self.db.flush()
        return u

    def h(self, user):
        return {"Authorization": f"Bearer {create_access_token(subject=str(user.id), extra_claims={'role': user.role})}"}

    def service(self, no="SRV_1", status_="New", logs=5):
        s = ServiceRequest(request_no=no, status=status_, customer_name="Customer", customer_mobile="9000000000")
        self.db.add(s)
        self.db.flush()
        for i in range(logs):
            self.db.add(ServiceStatusLog(service_request_id=s.id, action=f"step {i}", new_status=status_))
        self.db.commit()
        return s.id

    def count(self, model, **where):
        with self.Session() as s:
            return s.scalar(select(func.count()).select_from(model).where(*[getattr(model, k) == v for k, v in where.items()]))

    def test_admin_deletes_a_service_request_that_has_history(self):
        sid = self.service(logs=22)
        r = self.client.delete(f"/api/services/{sid}", headers=self.h(self.admin))
        self.assertEqual(r.status_code, 204, r.text)
        self.assertEqual(self.count(ServiceRequest, id=sid), 0)
        self.assertEqual(self.count(ServiceStatusLog, service_request_id=sid), 0, "the history goes with it")

    def test_sub_admin_can_too_and_the_other_requests_stay(self):
        a, b = self.service("SRV_A"), self.service("SRV_B")
        self.assertEqual(self.client.delete(f"/api/services/{a}", headers=self.h(self.sub)).status_code, 204)
        self.assertEqual(self.count(ServiceRequest, id=b), 1)
        self.assertEqual(self.count(ServiceStatusLog, service_request_id=b), 5)

    def test_an_engineer_cannot_delete(self):
        sid = self.service()
        r = self.client.delete(f"/api/services/{sid}", headers=self.h(self.eng))
        self.assertIn(r.status_code, (403, 404), r.text)
        self.assertEqual(self.count(ServiceRequest, id=sid), 1)

    def test_a_request_with_shortage_claims_is_not_deleted_and_says_why(self):
        sid = self.service()
        with self.Session() as s:
            for n in ("CLM-0001", "CLM-0002"):
                s.add(ShortageClaim(claim_no=n, flow="service", service_request_id=sid, description="copper pipe short", raised_by_user_id=self.admin.id))
            s.commit()
        r = self.client.delete(f"/api/services/{sid}", headers=self.h(self.admin))
        self.assertEqual(r.status_code, 400, r.text)
        self.assertIn("2 shortage claim(s)", r.json()["detail"])
        self.assertIn("CLM-0001", r.json()["detail"])
        self.assertEqual(self.count(ServiceRequest, id=sid), 1, "nothing was removed")
        self.assertEqual(self.count(ServiceStatusLog, service_request_id=sid), 5)

    def test_a_completed_request_still_cannot_be_deleted(self):
        sid = self.service(status_="Service Completed")
        r = self.client.delete(f"/api/services/{sid}", headers=self.h(self.admin))
        self.assertEqual(r.status_code, 400)
        self.assertEqual(self.count(ServiceRequest, id=sid), 1)


if __name__ == "__main__":
    unittest.main()
