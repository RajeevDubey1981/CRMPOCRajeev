from __future__ import annotations

import os
import sys
import unittest
from pathlib import Path
from unittest import mock

os.environ.setdefault("MYSQL_DATABASE_URL", "sqlite://")
os.environ["SARVAM_API_KEY"] = "test-key"
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.database import Base, get_db
from app.main import app
from app.models.email_confirmation import EmailConfirmation
from app.services import email_confirmation as svc

KEY = {"X-API-Key": "test-key"}


class EmailConfirmationTests(unittest.TestCase):
    def setUp(self):
        engine = create_engine("sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool)
        Base.metadata.create_all(engine)
        self.Session = sessionmaker(bind=engine, expire_on_commit=False)
        self.db = self.Session()

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

    def test_send_then_type_then_status(self):
        with mock.patch("app.services.sms_service.send_email_link_sms", return_value=True) as sms:
            r = self.client.post("/api/sarvam/email-link", json={"mobile": "9891572565", "name": "Ravi"}, headers=KEY)
        self.assertEqual(r.status_code, 200, r.text)
        code = sms.call_args.kwargs["code"]
        self.assertRegex(code, r"^[0-9]{6}$")
        s = self.client.get("/api/sarvam/email-link/status?mobile=9891572565", headers=KEY).json()["data"]
        self.assertEqual(s["status"], "waiting")
        bad = self.client.post("/api/public/email-confirm", json={"code": "000000", "email": "a@b.com"})
        self.assertEqual(bad.status_code, 400)
        ok = self.client.post("/api/public/email-confirm", json={"code": code, "email": "Ravi.K@Gmail.com"})
        self.assertEqual(ok.status_code, 200, ok.text)
        s = self.client.get("/api/sarvam/email-link/status?mobile=9891572565", headers=KEY).json()["data"]
        self.assertEqual((s["status"], s["email"]), ("confirmed", "ravi.k@gmail.com"))
        self.assertTrue(svc.confirmed_recently(self.db, "9891572565", "ravi.k@gmail.com"))
        self.assertFalse(svc.confirmed_recently(self.db, "9891572565", "other@gmail.com"))

    def test_sms_failure_is_reported(self):
        with mock.patch("app.services.sms_service.send_email_link_sms", return_value=False):
            r = self.client.post("/api/sarvam/email-link", json={"mobile": "9891572565"}, headers=KEY)
        self.assertEqual(r.status_code, 502)

    def test_needs_key_and_valid_mobile(self):
        self.assertEqual(self.client.post("/api/sarvam/email-link", json={"mobile": "9891572565"}).status_code, 401)
        self.assertEqual(self.client.post("/api/sarvam/email-link", json={"mobile": "123"}, headers=KEY).status_code, 422)

    def test_bad_email_rejected(self):
        row = svc.create_request(self.db, "9891572565", None)
        self.db.commit()
        r = self.client.post("/api/public/email-confirm", json={"code": row.code, "email": "not-an-email"})
        self.assertEqual(r.status_code, 400)


if __name__ == "__main__":
    unittest.main()
