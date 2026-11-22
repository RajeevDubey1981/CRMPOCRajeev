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
os.environ["SARVAM_KEEP_AUDIO_IN_CRM"] = "1"  # these tests cover the copy-in-CRM path; Drive links are tested below
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.database import Base, get_db
from app.main import app
from app.models import User
from app.models.call import Call, CallRecording
from app.models.complaint import Complaint
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

    def test_a_different_phone_still_links_when_it_is_the_only_call_in_that_time_window(self):
        r = self.hook(user_phone_number="+919000000000")
        self.assertEqual(r.json()["call_ref"], "CALL-1")

    def test_a_different_phone_with_two_calls_in_the_window_matches_nothing(self):
        with self.Session() as db:
            db.add(Call(ref_no="CALL-2", phone="9111111111", call_type="Inbound", status="Completed", priority="Medium",
                        call_datetime=self.at + timedelta(seconds=20), notes="Sarvam voice agent call (Sales), complaint IDC_2."))
            db.commit()
        r = self.hook(user_phone_number="+919000000000")
        self.assertEqual(r.json(), {"success": True, "matched": False})

    def test_phone_only_skips_a_time_only_match(self):
        with self.Session() as db:
            item = {"interaction_id": IID, "user_contact": "+919000000000", "duration_in_seconds": 90,
                    "start_datetime": (self.at - timedelta(seconds=40)).replace(tzinfo=None).isoformat(),
                    "end_datetime": (self.at + timedelta(seconds=55)).replace(tzinfo=None).isoformat()}
            strict = sarvam_recordings.link_interactions(db, [item], dry_run=True, allow_time_only=False)
            self.assertEqual((strict["matched"], strict["no_crm_call"]), (0, 1))
            loose = sarvam_recordings.link_interactions(db, [item], dry_run=True)
            self.assertEqual((loose["matched"], len(loose["time_only"])), (1, 1))

    def test_two_overlapping_calls_each_go_to_their_own_phone(self):
        with self.Session() as db:
            db.add(Call(ref_no="CALL-2", phone="9111111111", call_type="Inbound", status="Completed", priority="Medium",
                        call_datetime=self.at + timedelta(seconds=20), notes="Sarvam voice agent call (Sales), complaint IDC_2."))
            db.commit()
        r = self.hook(interaction_id="20261121/aaaaaaaa-1111", user_phone_number="+919111111111")
        self.assertEqual(r.json()["call_ref"], "CALL-2")
        r = self.hook(interaction_id="20261121/bbbbbbbb-2222", user_phone_number="+919876543210")
        self.assertEqual(r.json()["call_ref"], "CALL-1")

    def test_backfill_links_past_calls_once_and_never_twice(self):
        with self.Session() as db:
            old = self.at - timedelta(days=9)
            db.add(Call(ref_no="CALL-OLD", phone="9222222222", call_type="Inbound", status="Completed", priority="Medium",
                        call_datetime=old, notes="Sarvam voice agent call (Service), complaint IDC_9."))
            db.add(Call(ref_no="CALL-MANUAL", phone="9333333333", call_type="Outbound", status="Completed", priority="Medium",
                        call_datetime=old, notes="Manual call by the service desk."))
            db.commit()
            items = [
                {"interaction_id": "20261112/cccccccc-3333", "user_contact": "+919222222222", "duration_in_seconds": 71.4,
                 "start_datetime": (old - timedelta(seconds=30)).replace(tzinfo=None).isoformat(),
                 "end_datetime": (old + timedelta(seconds=40)).replace(tzinfo=None).isoformat()},
                {"interaction_id": "20261110/dddddddd-4444", "user_contact": "+919444444444", "duration_in_seconds": 5,
                 "start_datetime": (old - timedelta(days=2)).replace(tzinfo=None).isoformat(),
                 "end_datetime": (old - timedelta(days=2) + timedelta(seconds=5)).replace(tzinfo=None).isoformat()},
            ]
            dry = sarvam_recordings.link_interactions(db, items, dry_run=True)
            self.assertEqual((dry["matched"], dry["no_crm_call"]), (1, 1))
            self.assertEqual(dry["time_only"], [])  # matched on phone, not on time alone
            self.assertIsNone(db.query(Call).filter(Call.ref_no == "CALL-OLD").one().sarvam_interaction_id)  # dry run changes nothing
            done = sarvam_recordings.link_interactions(db, items)
            db.commit()
            self.assertEqual(done["pairs"], [("CALL-OLD", "20261112/cccccccc-3333")])
            row = db.query(Call).filter(Call.ref_no == "CALL-OLD").one()
            self.assertEqual((row.sarvam_interaction_id, row.duration_secs), ("20261112/cccccccc-3333", 71))
            self.assertIsNone(db.query(Call).filter(Call.ref_no == "CALL-MANUAL").one().sarvam_interaction_id)
            again = sarvam_recordings.link_interactions(db, items)
            self.assertEqual((again["matched"], again["already_linked"]), (0, 1))

    def test_webhook_rejects_a_malformed_interaction_id(self):
        self.assertEqual(self.hook(interaction_id="../../etc/passwd").status_code, 422)

    def test_real_sarvam_interaction_ids_with_colons_are_accepted_and_traversal_is_not(self):
        for good in ("20261023/bf9c14fd-10:08:55-5023b492", "20261121/9fc85ebc-21:35:39-aw188953", IID):
            self.assertTrue(sarvam_recordings.valid_interaction_id(good), good)
        for bad in ("../../etc/passwd", "20261023/../x", "20261023/a/b", "20261023/..", "x/abcdef", "20261023/ab cdef", ""):
            self.assertFalse(sarvam_recordings.valid_interaction_id(bad), bad)
        self.assertEqual(self.hook(interaction_id="20261121/9fc85ebc-21:35:39-aw188953").status_code, 200)

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

    def test_the_complaints_list_points_at_the_call_with_a_recording(self):
        with self.Session() as db:
            with_rec = Complaint(comp_no="IDC_A", customer_name="A", customer_mobile="9876543210", query_type="Service", status="Pending", source="callcenter")
            without = Complaint(comp_no="IDC_B", customer_name="B", customer_mobile="9000000001", query_type="Service", status="Pending", source="callcenter")
            db.add_all([with_rec, without])
            db.flush()
            call = db.get(Call, self.call_id)
            call.complaint_id, call.sarvam_interaction_id = with_rec.id, IID
            db.commit()
            a_id, b_id = with_rec.id, without.id
        r = self.client.get("/api/complaints", headers=self.admin_h())
        self.assertEqual(r.status_code, 200, r.text)
        rows = {i["id"]: i for i in r.json()["items"]}
        self.assertEqual(rows[a_id]["recording_call_id"], self.call_id)
        self.assertIsNone(rows[b_id]["recording_call_id"])

    def test_recording_needs_a_login(self):
        self.assertEqual(self.client.get(f"/api/calls/{self.call_id}/recording").status_code, 401)

    def test_not_configured_means_no_download_attempt(self):
        self.hook()
        with mock.patch.dict(os.environ, {"SARVAM_WORKSPACE_API_KEY": ""}):
            with mock.patch.object(sarvam_recordings.requests, "get", side_effect=AssertionError("must not call")):
                r = self.client.get(f"/api/calls/{self.call_id}/recording", headers=self.admin_h())
        self.assertEqual(r.status_code, 404)


class ShippedScriptsCompile(unittest.TestCase):
    def test_the_sarvam_scripts_compile(self):
        import py_compile

        root = Path(__file__).resolve().parents[1]
        for name in ("scripts/backfill_sarvam_recordings.py", "../scripts/set_sarvam_recording_keys.py"):
            py_compile.compile(str(root / name), doraise=True)


if __name__ == "__main__":
    unittest.main()


class SheetSyncTests(unittest.TestCase):
    def test_a_sheet_row_is_read_with_the_corrected_time_and_the_drive_link(self):
        sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
        import sync_sarvam_sheet as sync

        row = ["2026-07-31 1:16:16", "+919891572565", "0:29", "connected", "https://drive.google.com/file/d/1Ycuyix5jGyXaJGwv4REJmjbsSM9m9bXk/view",
               "20260731/2ec24523-06:46:10-02d3051c", "", "", "", "", "", "reason", "Resolved", "", "", "422"]
        item = sync.parse_row(row)
        self.assertEqual(item["start"], datetime(2026, 7, 31, 6, 46, 16, tzinfo=timezone.utc))  # sheet time + 5:30 = UTC
        self.assertEqual((item["duration"], item["complaint_no"]), (29, "422"))
        self.assertIsNone(sync.parse_row(["x"] * 16))

    def test_drive_file_id_is_taken_from_a_share_link(self):
        self.assertEqual(sarvam_recordings.drive_file_id("https://drive.google.com/file/d/1Ycuyix5jGyXaJGwv4REJmjbsSM9m9bXk/view?usp=drivesdk"), "1Ycuyix5jGyXaJGwv4REJmjbsSM9m9bXk")
        self.assertIsNone(sarvam_recordings.drive_file_id("https://example.com/x"))


class CallPurposeTests(unittest.TestCase):
    def test_purpose_is_read_from_the_call_summary(self):
        from app.services.call_purpose import clean_purpose, infer_purpose

        self.assertEqual(infer_purpose("Wants a dealership for Noida"), "Business or dealer enquiry")
        self.assertEqual(infer_purpose("AC shows E6 error, technician needed"), "Service complaint")
        self.assertEqual(infer_purpose("Asked the price of a 1.5 ton split"), "Sales enquiry")
        self.assertEqual(infer_purpose("Applying for a job"), "Job or HR")
        self.assertEqual(infer_purpose(""), "Other")
        self.assertEqual(clean_purpose(" sales enquiry "), "Sales enquiry")
        self.assertIsNone(clean_purpose("nonsense"))
