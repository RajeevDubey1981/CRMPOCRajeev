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
from app.models.user_query import UserQueryAttachment
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
        self.assertEqual(last["attachments"][0]["url"], f"/api/queries/attachments/{last['attachments'][0]['id']}/download")
        self.assertNotIn("file_path", last["attachments"][0], "the place on disk is never shown")
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

    def test_any_file_up_to_2_mb_is_accepted_but_not_programs_or_bigger_ones(self):
        for name, data, mime in (("report.pdf", b"%PDF-1.4 x", "application/pdf"), ("notes.txt", b"hello", "text/plain"), ("sheet.xlsx", b"PKx", "application/octet-stream"), ("data.csv", b"a,b", "text/csv")):
            self.assertEqual(self.upload(self.eng, name, data, mime).status_code, 201, name)
        self.assertEqual(self.upload(self.eng, "ok.bin", b"x" * (2 * 1024 * 1024), "application/octet-stream").status_code, 201, "exactly 2 MB is fine")
        self.assertEqual(self.upload(self.eng, "big.bin", b"x" * (2 * 1024 * 1024 + 1), "application/octet-stream").status_code, 413)
        self.assertEqual(self.upload(self.eng, "run.exe", b"MZ" + b"\x00" * 20, "application/octet-stream").status_code, 400)
        self.assertEqual(self.upload(self.eng, "empty.txt", b"", "text/plain").status_code, 400)

    def test_a_fake_picture_only_downloads_it_is_never_shown_as_one(self):
        up = self.upload(self.eng, "fake.png", b"not really a png", "image/png")
        self.assertEqual(up.status_code, 201)
        self.assertFalse(up.json()["is_image"])

    def test_everyone_in_the_conversation_can_download_it_and_nobody_else(self):
        up = self.upload(self.eng, "report.pdf", b"%PDF-1.4 hello", "application/pdf").json()
        self.assertEqual(self.client.get(up["url"], headers=self.h(self.eng)).status_code, 200, "the one adding it, before sending")
        self.assertEqual(self.client.get(up["url"], headers=self.h(self.admin)).status_code, 404, "not sent yet: private to the uploader")
        self.reply(self.eng, "here", [up["id"]])
        mine = self.client.get(up["url"], headers=self.h(self.eng))
        self.assertEqual((mine.status_code, mine.content), (200, b"%PDF-1.4 hello"))
        self.assertIn("attachment", mine.headers["content-disposition"])
        self.assertIn("report.pdf", mine.headers["content-disposition"])
        self.assertEqual(mine.headers["x-content-type-options"], "nosniff")
        self.assertEqual(self.client.get(up["url"], headers=self.h(self.admin)).status_code, 200, "the Admin team")
        self.assertEqual(self.client.get(up["url"], headers=self.h(self.other)).status_code, 404, "someone not in it")
        self.assertEqual(self.client.get(up["url"]).status_code, 401, "not signed in")
        # added to the conversation, they can download it too
        sub = self._user("sub@t.com", "sub_admin")
        self.db.commit()
        self.client.post(f"/api/queries/{self.qid}/members", json={"user_id": self.other.id, "kind": "member", "share_history": True}, headers=self.h(sub))
        self.assertEqual(self.client.get(up["url"], headers=self.h(self.other)).status_code, 200)

    def test_a_picture_shows_inline_for_the_thread_and_the_files_are_not_public_links(self):
        up = self.upload(self.eng).json()
        self.reply(self.eng, "", [up["id"]])
        shown = self.client.get(up["url"], params={"inline": True}, headers=self.h(self.eng))
        self.assertEqual(shown.headers["content-type"], "image/png")
        self.assertIn("inline", shown.headers["content-disposition"])
        with self.Session() as s:
            public = s.get(UserQueryAttachment, up["id"]).file_path
        self.assertEqual(self.client.get(public).status_code, 404, "the old public address no longer works")

    def test_nobody_can_send_someone_elses_or_an_already_used_upload(self):
        up = self.upload(self.eng).json()["id"]
        self.assertEqual(self.reply(self.admin, "mine?", [up]).status_code, 400)
        self.assertEqual(self.reply(self.eng, "ok", [up]).status_code, 200)
        self.assertEqual(self.reply(self.eng, "again", [up]).status_code, 400, "a file goes with one message only")


if __name__ == "__main__":
    unittest.main()
