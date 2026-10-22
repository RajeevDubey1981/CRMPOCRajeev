from __future__ import annotations

import os
import sys
import tempfile
import unittest
from datetime import timedelta
from pathlib import Path

os.environ.setdefault("MYSQL_DATABASE_URL", "sqlite://")
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from fastapi.testclient import TestClient
from sqlalchemy import create_engine, func, select
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.config import settings
from app.database import Base, get_db
from app.main import app
from app.models import User
from app.models.user_query import (
    UserQuery, UserQueryAttachment, UserQueryEvent, UserQueryMember, UserQueryMessage, UserQueryPurge, UserQueryRead,
)
from app.security import create_access_token, hash_password
from app.seed import seed_roles
from app.services import queries_service as qs

PNG = b"\x89PNG\r\n\x1a\n" + b"\x00" * 64


class QueryPurgeTests(unittest.TestCase):
    """A conversation is deleted for good six months after it was closed, with its pictures and files."""

    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self._old_upload = settings.upload_dir
        settings.upload_dir = self._tmp.name
        engine = create_engine("sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool)
        Base.metadata.create_all(engine)
        self.Session = sessionmaker(bind=engine, autoflush=False, autocommit=False, future=True)
        self.db = self.Session()
        seed_roles(self.db)
        self.admin = self._user("admin@t.com", "admin")
        self.eng = self._user("eng@t.com", "engineer")
        self.db.commit()

        def override():
            s = self.Session()
            try:
                yield s
            finally:
                s.close()

        app.dependency_overrides[get_db] = override
        self.client = TestClient(app)

    def tearDown(self):
        app.dependency_overrides.clear()
        self.db.close()
        settings.upload_dir = self._old_upload
        self._tmp.cleanup()

    def _user(self, email, role):
        u = User(name=email.split("@")[0], email=email, password_hash=hash_password("pw123456"), role=role, is_active=True)
        self.db.add(u)
        self.db.flush()
        return u

    def h(self, user):
        return {"Authorization": f"Bearer {create_access_token(subject=str(user.id), extra_claims={'role': user.role})}"}

    def conversation(self, with_picture=True):
        qid = self.client.post("/api/queries", json={"subject": "Order", "message": "Hello"}, headers=self.h(self.eng)).json()["id"]
        path = None
        if with_picture:
            up = self.client.post("/api/queries/attachments", files={"file": ("shot.png", PNG, "image/png")}, headers=self.h(self.eng)).json()
            self.client.post(f"/api/queries/{qid}/messages", json={"body": "see", "attachment_ids": [up["id"]]}, headers=self.h(self.eng))
            with self.Session() as s:
                path = s.get(UserQueryAttachment, up["id"]).file_path
        return qid, path

    def close(self, qid, days_ago):
        with self.Session() as s:
            q = s.get(UserQuery, qid)
            q.status = "Closed"
            q.closed_at = qs.now() - timedelta(days=days_ago)
            s.commit()

    def count(self, model):
        with self.Session() as s:
            return s.scalar(select(func.count()).select_from(model))

    def purge(self):
        with self.Session() as s:
            return qs.purge_closed(s)

    def test_a_conversation_closed_over_three_months_ago_goes_with_everything_in_it(self):
        qid, path = self.conversation()
        self.assertTrue(any(Path(self._tmp.name).rglob("*.png")), "the picture is on disk")
        self.close(qid, 181)
        self.assertEqual(self.purge(), 1)
        for model in (UserQuery, UserQueryMessage, UserQueryAttachment, UserQueryMember, UserQueryEvent, UserQueryRead):
            self.assertEqual(self.count(model), 0, model.__name__)
        self.assertFalse(any(Path(self._tmp.name).rglob("*.png")), "the file is deleted too")
        with self.Session() as s:
            record = s.scalars(select(UserQueryPurge)).one()
        self.assertEqual((record.query_no, record.message_count, record.attachment_count), (f"QRY-{qid:04d}", 2, 1))

    def test_open_answered_and_recently_closed_conversations_stay(self):
        open_id, _ = self.conversation(False)
        recent_id, _ = self.conversation(False)
        edge_id, _ = self.conversation(False)
        self.close(recent_id, 60)
        self.close(edge_id, 179)
        self.assertEqual(self.purge(), 0)
        self.assertEqual(self.count(UserQuery), 3)
        self.assertEqual(self.client.get(f"/api/queries/{open_id}", headers=self.h(self.eng)).json()["delete_on"], None)

    def test_a_reopened_conversation_is_not_deleted(self):
        qid, _ = self.conversation(False)
        self.close(qid, 200)
        self.assertEqual(self.client.post(f"/api/queries/{qid}/reopen", headers=self.h(self.admin)).status_code, 200)
        self.assertEqual(self.purge(), 0)
        self.assertEqual(self.count(UserQuery), 1)

    def test_the_closed_conversation_says_when_it_will_be_deleted(self):
        qid, _ = self.conversation(False)
        self.close(qid, 10)
        shown = self.client.get(f"/api/queries/{qid}", headers=self.h(self.admin)).json()["delete_on"]
        from datetime import datetime, timezone

        when = datetime.fromisoformat(shown)
        if when.tzinfo is None:
            when = when.replace(tzinfo=timezone.utc)
        self.assertIn((when - qs.now()).days, (169, 170), "ten days after closing leaves about 170")

    def test_only_one_conversation_goes_and_the_others_keep_their_files(self):
        old, _ = self.conversation()
        keep, _ = self.conversation()
        self.close(old, 190)
        self.assertEqual(self.purge(), 1)
        self.assertEqual(self.count(UserQuery), 1)
        self.assertEqual(len(list(Path(self._tmp.name).rglob("*.png"))), 1)


if __name__ == "__main__":
    unittest.main()
