from __future__ import annotations

import os
import sys
import tempfile
import unittest
from pathlib import Path

os.environ.setdefault("MYSQL_DATABASE_URL", "sqlite://")
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.config import settings
from app.database import Base, get_db
from app.main import app
from app.models import User
from app.security import create_access_token, hash_password
from app.seed import seed_roles

PNG = b"\x89PNG\r\n\x1a\n" + b"\x00" * 64


class QueryAttachmentTests(unittest.TestCase):
    """A screenshot pasted into the Query chat is uploaded, then sent with (or without) words."""

    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self._old_upload = getattr(settings, "upload_dir", None)
        try:
            settings.upload_dir = self._tmp.name
        except Exception:
            pass
        engine = create_engine("sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool)
        Base.metadata.create_all(engine)
        self.Session = sessionmaker(bind=engine, autoflush=False, autocommit=False, future=True)
        self.db = self.Session()
        seed_roles(self.db)
        self.admin = self._user("admin@t.com", "admin")
        self.eng = self._user("eng@t.com", "engineer")
        self.other = self._user("other@t.com", "engineer")
        self.db.commit()

        def override():
            s = self.Session()
            try:
                yield s
            finally:
                s.close()

        app.dependency_overrides[get_db] = override
        self.client = TestClient(app)
        r = self.client.post("/api/queries", json={"subject": "Order", "message": "Hello"}, headers=self.h(self.eng))
        self.qid = r.json()["id"]

    def tearDown(self):
        app.dependency_overrides.clear()
        self.db.close()
        if self._old_upload is not None:
            settings.upload_dir = self._old_upload
        self._tmp.cleanup()

    def _user(self, email, role):
        u = User(name=email.split("@")[0], email=email, password_hash=hash_password("pw123456"), role=role, is_active=True)
        self.db.add(u)
        self.db.flush()
        return u

    def h(self, user):
        return {"Authorization": f"Bearer {create_access_token(subject=str(user.id), extra_claims={'role': user.role})}"}

    def upload(self, user, name="screenshot.png", data=PNG, mime="image/png"):
        return self.client.post("/api/queries/attachments", files={"file": (name, data, mime)}, headers=self.h(user))

    def reply(self, user, body="", ids=()):
        return self.client.post(f"/api/queries/{self.qid}/messages", json={"body": body, "attachment_ids": list(ids)}, headers=self.h(user))

    def test_a_pasted_screenshot_goes_with_the_words_and_shows_in_the_thread(self):
        up = self.upload(self.eng)
        self.assertEqual(up.status_code, 201, up.text)
        self.assertTrue(up.json()["is_image"])
        r = self.reply(self.eng, "See this", [up.json()["id"]])
        self.assertEqual(r.status_code, 200, r.text)
        last = r.json()["messages"][-1]
        self.assertEqual(last["body"], "See this")
        self.assertEqual([a["file_name"] for a in last["attachments"]], ["screenshot.png"])
        self.assertIn("queries", last["attachments"][0]["file_path"])
        self.assertTrue(last["attachments"][0]["file_path"].endswith(".png"))
        # the other side reads it too
        seen = self.client.get(f"/api/queries/{self.qid}", headers=self.h(self.admin)).json()["messages"][-1]
        self.assertEqual(len(seen["attachments"]), 1)

    def test_a_picture_can_be_sent_on_its_own(self):
        up = self.upload(self.eng)
        r = self.reply(self.eng, "", [up.json()["id"]])
        self.assertEqual(r.status_code, 200, r.text)
        self.assertEqual(r.json()["messages"][-1]["body"], "")
        listing = self.client.get("/api/queries", headers=self.h(self.eng)).json()
        self.assertEqual(listing[0]["last_message_preview"], "Sent a picture")

    def test_nothing_to_send_is_refused(self):
        self.assertEqual(self.reply(self.eng, "", []).status_code, 422)

    def test_only_pictures_and_documents_are_accepted(self):
        self.assertEqual(self.upload(self.eng, "run.exe", b"MZ" + b"\x00" * 20, "application/octet-stream").status_code, 400)
        self.assertEqual(self.upload(self.eng, "fake.png", b"not really a png", "image/png").status_code, 400)

    def test_nobody_can_send_someone_elses_or_an_already_used_upload(self):
        up = self.upload(self.eng).json()["id"]
        self.assertEqual(self.reply(self.admin, "mine?", [up]).status_code, 400)
        self.assertEqual(self.reply(self.eng, "ok", [up]).status_code, 200)
        self.assertEqual(self.reply(self.eng, "again", [up]).status_code, 400, "a file goes with one message only")


if __name__ == "__main__":
    unittest.main()
