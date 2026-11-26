from __future__ import annotations

import os
import sys
import unittest
from datetime import date
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


class ServiceRequestFilterTests(unittest.TestCase):
    def setUp(self):
        engine = create_engine("sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool)
        Base.metadata.create_all(engine)
        self.Session = sessionmaker(bind=engine, expire_on_commit=False)
        self.db = self.Session()
        seed_roles(self.db)
        self.admin = User(name="Admin", email="a@x.com", password_hash=hash_password("x"), role="admin", is_active=True)
        self.db.add(self.admin)
        self.db.commit()
        c = Complaint(comp_no="IDC_1794631173744", comp_date=date.today(), customer_name="N", customer_mobile="9876543210",
                      query_type="Service", status="Rejected", access_code="1234")
        self.db.add(c)
        self.db.flush()
        self.db.add(ServiceRequest(request_no="SRV_1794631173750", complaint_id=c.id, status="Service Team Review", query_type="Service", customer_name="N", customer_mobile="9876543210", problem_description="p"))
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

    def h(self):
        return {"Authorization": f"Bearer {create_access_token(subject=str(self.admin.id), extra_claims={'role': 'admin'})}"}

    def test_srv_number_finds_its_complaint(self):
        r = self.client.get("/api/complaints?comp_no=SRV_1794631173750", headers=self.h())
        self.assertEqual(r.status_code, 200, r.text)
        self.assertEqual([x["comp_no"] for x in r.json()["items"]], ["IDC_1794631173744"])

    def test_complaint_number_still_works(self):
        r = self.client.get("/api/complaints?comp_no=IDC_1794631173744", headers=self.h())
        self.assertEqual(len(r.json()["items"]), 1)

    def test_unknown_number_finds_nothing(self):
        r = self.client.get("/api/complaints?comp_no=SRV_999", headers=self.h())
        self.assertEqual(r.json()["items"], [])


if __name__ == "__main__":
    unittest.main()
