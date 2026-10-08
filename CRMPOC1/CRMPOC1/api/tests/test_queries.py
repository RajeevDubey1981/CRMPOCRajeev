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
from app.security import create_access_token, hash_password
from app.seed import seed_roles


class QueriesTests(unittest.TestCase):
    def setUp(self):
        engine = create_engine("sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool)
        Base.metadata.create_all(engine)
        self.Session = sessionmaker(bind=engine, autoflush=False, autocommit=False, future=True)
        self.db = self.Session()
        seed_roles(self.db)

        def override():
            s = self.Session()
            try:
                yield s
            finally:
                s.close()

        app.dependency_overrides[get_db] = override
        self.client = TestClient(app)
        self.admin = self._user("admin@t.com", "admin")
        self.sub = self._user("sub@t.com", "sub_admin")
        self.eng = self._user("eng@t.com", "engineer")
        self.eng2 = self._user("eng2@t.com", "engineer")
        self.vendor = self._user("v@t.com", "vendor")
        self.tech = self._user("tech@t.com", "service_manager")
        self.db.commit()

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

    def raise_query(self, user, subject="Payment not received", message="My payment is pending since last week"):
        r = self.client.post("/api/queries", json={"subject": subject, "category": "Payment", "related_to": "INS-12", "message": message}, headers=self.h(user))
        self.assertEqual(r.status_code, 201, r.text)
        return r.json()

    def test_anyone_can_raise_a_query_and_admin_and_sub_admin_both_see_it(self):
        for user in (self.eng, self.vendor, self.tech):
            q = self.raise_query(user, subject=f"Help from {user.name}")
            self.assertEqual(q["status"], "Open")
            self.assertEqual(q["messages"][0]["mine"], True)
        for staff in (self.admin, self.sub):
            rows = self.client.get("/api/queries", headers=self.h(staff)).json()
            self.assertEqual(len(rows), 3)
            self.assertTrue(all(r["unread_count"] == 1 for r in rows), "new for the staff")
            summary = self.client.get("/api/queries/summary", headers=self.h(staff)).json()
            self.assertEqual((summary["open"], summary["unread"], summary["staff"]), (3, 3, True))

    def test_people_only_see_their_own_queries(self):
        mine = self.raise_query(self.eng)
        other = self.raise_query(self.vendor, subject="Bid question")
        rows = self.client.get("/api/queries", headers=self.h(self.eng)).json()
        self.assertEqual([r["id"] for r in rows], [mine["id"]])
        self.assertEqual(self.client.get(f"/api/queries/{other['id']}", headers=self.h(self.eng)).status_code, 404)
        self.assertEqual(self.client.post(f"/api/queries/{other['id']}/messages", json={"body": "hi"}, headers=self.h(self.eng)).status_code, 404)
        self.assertEqual(self.client.post(f"/api/queries/{other['id']}/close", headers=self.h(self.eng)).status_code, 404)

    def test_the_conversation_goes_back_and_forth_with_unread_counts(self):
        q = self.raise_query(self.eng)
        url = f"/api/queries/{q['id']}"
        opened = self.client.get(url, headers=self.h(self.admin)).json()
        self.assertEqual(opened["unread_count"], 1, "shown as new the first time it is opened")
        self.assertEqual(self.client.get("/api/queries/summary", headers=self.h(self.admin)).json()["unread"], 0, "then it is read")
        self.assertEqual(self.client.get("/api/queries/summary", headers=self.h(self.sub)).json()["unread"], 1, "reading is kept per person")

        r = self.client.post(f"{url}/messages", json={"body": "Sent to accounts, it will be paid tomorrow."}, headers=self.h(self.admin))
        self.assertEqual(r.status_code, 200, r.text)
        self.assertEqual(r.json()["status"], "Answered")
        self.assertTrue(r.json()["messages"][-1]["from_staff"])
        mine = self.client.get("/api/queries/summary", headers=self.h(self.eng)).json()
        self.assertEqual((mine["answered"], mine["unread"], mine["staff"]), (1, 1, False))
        self.assertEqual(self.client.get("/api/queries", headers=self.h(self.eng)).json()[0]["unread_count"], 1)

        seen = self.client.get(url, headers=self.h(self.eng)).json()
        self.assertEqual([m["mine"] for m in seen["messages"]], [True, False])
        self.assertEqual(self.client.get("/api/queries/summary", headers=self.h(self.eng)).json()["unread"], 0)

        again = self.client.post(f"{url}/messages", json={"body": "Thank you, but the amount is short."}, headers=self.h(self.eng)).json()
        self.assertEqual(again["status"], "Open", "an answer from the user puts it back to the staff")
        sub = self.client.get("/api/queries", params={"status": "Open"}, headers=self.h(self.sub)).json()
        self.assertEqual((len(sub), sub[0]["unread_count"], sub[0]["last_sender_name"]), (1, 3, "eng"))

    def test_closing_and_reopening(self):
        q = self.raise_query(self.eng)
        url = f"/api/queries/{q['id']}"
        self.client.post(f"{url}/close", headers=self.h(self.sub))
        closed = self.client.get(url, headers=self.h(self.eng)).json()
        self.assertEqual((closed["status"], closed["can_reopen"], closed["can_reply"]), ("Closed", True, False))
        self.assertEqual(self.client.post(f"{url}/messages", json={"body": "one more thing"}, headers=self.h(self.eng)).status_code, 400)
        self.assertEqual(self.client.post(f"{url}/messages", json={"body": "Reopening, sorry"}, headers=self.h(self.admin)).json()["status"], "Answered")
        self.client.post(f"{url}/close", headers=self.h(self.eng))
        self.assertEqual(self.client.post(f"{url}/reopen", headers=self.h(self.eng)).json()["status"], "Open")
        self.assertEqual(len(self.client.get("/api/queries", params={"status": "Active"}, headers=self.h(self.eng)).json()), 1)

    def test_admin_can_write_to_a_user_first_but_nobody_else_can(self):
        r = self.client.post("/api/queries", json={"subject": "Please upload your documents", "message": "Upload your ID proof today.", "to_user_id": self.eng2.id}, headers=self.h(self.sub))
        self.assertEqual(r.status_code, 201, r.text)
        self.assertEqual((r.json()["status"], r.json()["owner_id"]), ("Answered", self.eng2.id))
        self.assertEqual(self.client.get("/api/queries/summary", headers=self.h(self.eng2)).json()["unread"], 1)
        self.assertEqual(self.client.get("/api/queries/summary", headers=self.h(self.sub)).json()["unread"], 0)
        reply = self.client.post(f"/api/queries/{r.json()['id']}/messages", json={"body": "Done, uploaded."}, headers=self.h(self.eng2)).json()
        self.assertEqual(reply["status"], "Open")
        self.assertEqual(self.client.post("/api/queries", json={"subject": "x", "message": "y", "to_user_id": self.vendor.id}, headers=self.h(self.eng)).status_code, 403)
        self.assertEqual(self.client.post("/api/queries", json={"subject": "x", "message": "y"}, headers=self.h(self.admin)).status_code, 400, "staff must say who")
        self.assertEqual(self.client.post("/api/queries", json={"subject": "x", "message": "y", "to_user_id": 9999}, headers=self.h(self.admin)).status_code, 404)

    def test_search_and_empty_messages(self):
        self.raise_query(self.eng, subject="Payment not received")
        self.raise_query(self.vendor, subject="Bid date question")
        names = lambda **p: sorted(r["subject"] for r in self.client.get("/api/queries", params=p, headers=self.h(self.admin)).json())
        self.assertEqual(names(search="bid"), ["Bid date question"])
        self.assertEqual(names(search="vendor"), [], "searches the subject, the reference and the person's name")
        self.assertEqual(names(search="v@t"), ["Bid date question"])
        self.assertEqual(names(search="INS-12"), ["Bid date question", "Payment not received"])
        bad = self.client.post("/api/queries", json={"subject": "  ", "message": "text"}, headers=self.h(self.eng))
        self.assertEqual(bad.status_code, 422)
        bad = self.client.post("/api/queries", json={"subject": "ok", "message": "   "}, headers=self.h(self.eng))
        self.assertEqual(bad.status_code, 422)
        odd = self.client.post("/api/queries", json={"subject": "ok", "category": "Nonsense", "message": "hello"}, headers=self.h(self.eng))
        self.assertEqual(odd.json()["category"], "General")


if __name__ == "__main__":
    unittest.main()
