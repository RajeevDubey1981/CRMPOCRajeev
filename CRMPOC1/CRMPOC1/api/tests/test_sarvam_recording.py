from __future__ import annotations

import os
import sys
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path
from unittest import mock

os.environ.setdefault("MYSQL_DATABASE_URL", "sqlite://")
os.environ["SARVAM_API_KEY"] = "test-key"
os.environ["SARVAM_ORG_ID"] = "org1"
os.environ["SARVAM_WORKSPACE_ID"] = "ws1"
os.environ["SARVAM_APP_ID"] = "app1"
os.environ["SARVAM_WORKSPACE_API_KEY"] = "ws-secret"
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.database import Base, get_db
from app.main import app
from app.models import User
from app.models.call import Call, CallRecording
from app.routers import sarvam_api
from app.security import create_access_token, hash_password
from app.seed import seed_roles
from app.services import sarvam_recordings

IID = "20261121/9f1c2a7e-4b3d-4e8a-a1f0-6c2d9b7e5a14"


class _Resp:
    def __init__(self, status=200, body=b"RIFF....WAVEfmt ", ctype="audio/wav"):
        self.status_code, self._body, self.headers = status, body, {"Content-Type": ctype}

    def iter_content(self, n):
        yield self._body

    def __enter__(self):
        return self

    def __exit__(self, *a):
        return False


class SarvamRecordingTests(unittest.TestCase):
    def setUp(self):
        engine = create_engine("sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool)
        Base.metadata.create_all(engine)
        self.Session = sessionmaker(bind=engine, autoflush=False, autocommit=False, future=True)
        self.db = self.Session()
        seed_roles(self.db)
        self.admin = User(name="Admin", email="a@t.com", password_hash=hash_password("pw123456"), role="admin", is_active=True)
        self.db.add(self.admin)
        self.at = datetime.now(timezone.utc).replace(microsecond=0)
        self.call = Call(
            ref_no="CALL-1", customer_name="Imran", phone="9876543210", call_type="Inbound", status="Completed",
            priority="Medium", call_datetime=self.at, notes="Sarvam voice agent call (Service), complaint IDC_1.",
        )
        self.db.add(self.call)
        self.db.commit()
        self.call_id = self.call.id

        def override():
            sess = self.Session()
            try:
                yield sess
            finally:
                sess.close()

        app.dependency_overrides[get_db] = override
        self.client = TestClient(app, raise_server_exceptions=False)
        # Don't let the webhook start its retry thread against the real network in tests.
        self._thread = mock.patch.object(sarvam_api.threading, "Thread")
        self._thread.start()

    def tearDown(self):
        self._thread.stop()
        app.dependency_overrides.clear()
        self.db.close()

    def admin_h(self):
        return {"Authorization": f"Bearer {create_access_token(subject=str(self.admin.id), extra_claims={'role': 'admin'})}"}

    def hook(self, **over):
        body = {
            "interaction_id": IID, "user_phone_number": "+919876543210", "duration": 95,
            "start_datetime": (self.at - timedelta(seconds=40)).isoformat(),
            "end_datetime": (self.at + timedelta(seconds=55)).isoformat(),
        }
        body.update(over)
        return self.client.post("/api/sarvam/call-completed", json=body, headers={"X-API-Key": "test-key"})

    def test_webhook_needs_credentials(self):
        r = self.client.post("/api/sarvam/call-completed", json={"interaction_id": IID})
        self.assertEqual(r.status_code, 401)

    def test_webhook_ties_the_interaction_to_the_call_by_phone_and_time(self):
        r = self.hook()
        self.assertEqual(r.status_code, 200, r.text)
        self.assertEqual(r.json()["call_ref"], "CALL-1")
        call = self.Session().get(Call, self.call_id)
        self.assertEqual((call.sarvam_interaction_id, call.duration_secs), (IID, 95))

    def test_webhook_for_an_unknown_caller_matches_nothing(self):
        r = self.hook(user_phone_number="+919000000000")
        self.assertEqual(r.json(), {"success": True, "matched": False})

    def test_webhook_rejects_a_malformed_interaction_id(self):
        self.assertEqual(self.hook(interaction_id="../../etc/passwd").status_code, 422)

    def test_first_play_downloads_keeps_and_then_serves_from_the_crm(self):
        self.hook()
        with mock.patch.object(sarvam_recordings.requests, "get", return_value=_Resp()) as get:
            r = self.client.get(f"/api/calls/{self.call_id}/recording", headers=self.admin_h())
            self.assertEqual(r.status_code, 200, r.text)
            self.assertTrue(r.content.startswith(b"RIFF"))
            self.assertEqual(r.headers["content-type"], "audio/wav")
            url, kwargs = get.call_args[0][0], get.call_args[1]
            self.assertEqual(url, f"https://apps.sarvam.ai/api/analytics/v1/org1/ws1/app1/recordings/{IID}")
            self.assertEqual(kwargs["headers"], {"X-API-Key": "ws-secret"})
        self.assertEqual(self.Session().query(CallRecording).count(), 1)
        # second play comes from the CRM, Sarvam isn't asked again
        with mock.patch.object(sarvam_recordings.requests, "get", side_effect=AssertionError("asked Sarvam again")):
            self.assertEqual(self.client.get(f"/api/calls/{self.call_id}/recording", headers=self.admin_h()).status_code, 200)

    def test_no_recording_at_sarvam_is_a_clean_404(self):
        self.hook()
        with mock.patch.object(sarvam_recordings.requests, "get", return_value=_Resp(status=404)):
            r = self.client.get(f"/api/calls/{self.call_id}/recording", headers=self.admin_h())
        self.assertEqual(r.status_code, 404)

    def test_a_call_without_an_interaction_id_has_no_recording_flag(self):
        r = self.client.get(f"/api/calls/{self.call_id}", headers=self.admin_h())
        self.assertFalse(r.json()["has_recording"])
        self.hook()
        r = self.client.get(f"/api/calls/{self.call_id}", headers=self.admin_h())
        self.assertTrue(r.json()["has_recording"])

    def test_recording_needs_a_login(self):
        self.assertEqual(self.client.get(f"/api/calls/{self.call_id}/recording").status_code, 401)

    def test_not_configured_means_no_download_attempt(self):
        self.hook()
        with mock.patch.dict(os.environ, {"SARVAM_WORKSPACE_API_KEY": ""}):
            with mock.patch.object(sarvam_recordings.requests, "get", side_effect=AssertionError("must not call")):
                r = self.client.get(f"/api/calls/{self.call_id}/recording", headers=self.admin_h())
        self.assertEqual(r.status_code, 404)


if __name__ == "__main__":
    unittest.main()
