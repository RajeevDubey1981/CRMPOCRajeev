from __future__ import annotations

import hashlib
import hmac
import json
import os
import sys
import time
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path
from unittest import mock

os.environ.setdefault("MYSQL_DATABASE_URL", "sqlite://")
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from fastapi.testclient import TestClient
from sqlalchemy import create_engine, select
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.config import settings
from app.database import Base, get_db
from app.main import app
from app.models import User
from app.models.whatsapp import WaConversation, WaMessage, WaWebhookEvent
from app.security import create_access_token, hash_password
from app.seed import seed_roles
from app.services import whatsapp_inbox as wa

SECRET = "test-app-secret"
PHONE = "919891572565"


def payload(msg_id="wamid.A1", text="Hello", ts=None, number_id="111222333"):
    return {
        "object": "whatsapp_business_account",
        "entry": [{"id": "waba", "changes": [{"field": "messages", "value": {
            "messaging_product": "whatsapp",
            "metadata": {"display_phone_number": "9100000000", "phone_number_id": number_id},
            "contacts": [{"wa_id": PHONE, "profile": {"name": "Ravi"}}],
            "messages": [{"from": PHONE, "id": msg_id, "timestamp": str(ts or int(time.time())), "type": "text", "text": {"body": text}}],
        }}]}],
    }


def status_payload(msg_id, status, number_id="111222333"):
    return {"entry": [{"changes": [{"field": "messages", "value": {
        "metadata": {"phone_number_id": number_id}, "statuses": [{"id": msg_id, "status": status, "recipient_id": PHONE}]}}]}]}


def sign(raw: bytes) -> str:
    return "sha256=" + hmac.new(SECRET.encode(), raw, hashlib.sha256).hexdigest()


class WhatsAppInboxTests(unittest.TestCase):
    def setUp(self):
        self._patches = [
            mock.patch.object(settings, "meta_app_secret", SECRET),
            mock.patch.object(settings, "wa_verify_token", "verify-me"),
            mock.patch.object(settings, "wa_phone_number_id", "111222333"),
            mock.patch.object(settings, "wa_access_token", "tok"),
            mock.patch.object(settings, "whatsapp_enabled", True),
        ]
        for p in self._patches:
            p.start()
        engine = create_engine("sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool)
        Base.metadata.create_all(engine)
        self.Session = sessionmaker(bind=engine, expire_on_commit=False)
        self.db = self.Session()
        seed_roles(self.db)
        self.admin = User(name="Admin", email="a@x.com", password_hash=hash_password("x"), role="admin", is_active=True)
        self.eng = User(name="Eng", email="e@x.com", password_hash=hash_password("x"), role="engineer", is_active=True)
        self.db.add_all([self.admin, self.eng])
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
        for p in self._patches:
            p.stop()

    def post(self, body: dict, sig: str | None = "auto"):
        raw = json.dumps(body).encode()
        headers = {"Content-Type": "application/json"}
        if sig == "auto":
            headers["X-Hub-Signature-256"] = sign(raw)
        elif sig:
            headers["X-Hub-Signature-256"] = sig
        return self.client.post("/api/whatsapp/webhook", content=raw, headers=headers)

    def h(self, u):
        return {"Authorization": f"Bearer {create_access_token(subject=str(u.id), extra_claims={'role': u.role})}"}

    # --- verification and signature ---
    def test_verify_challenge(self):
        ok = self.client.get("/api/whatsapp/webhook?hub.mode=subscribe&hub.verify_token=verify-me&hub.challenge=777")
        self.assertEqual((ok.status_code, ok.text), (200, "777"))
        bad = self.client.get("/api/whatsapp/webhook?hub.mode=subscribe&hub.verify_token=nope&hub.challenge=777")
        self.assertEqual(bad.status_code, 403)

    def test_bad_or_missing_signature_is_rejected_and_nothing_is_stored(self):
        self.assertEqual(self.post(payload(), sig="sha256=deadbeef").status_code, 401)
        self.assertEqual(self.post(payload(), sig=None).status_code, 401)
        self.assertEqual(self.db.scalar(select(WaMessage.id)), None)

    def test_the_whatsapp_app_secret_is_accepted_too(self):
        with mock.patch.object(settings, "wa_app_secret", "other-app-secret"):
            raw = json.dumps(payload("wamid.W1")).encode()
            sig = "sha256=" + hmac.new(b"other-app-secret", raw, hashlib.sha256).hexdigest()
            r = self.client.post("/api/whatsapp/webhook", content=raw, headers={"Content-Type": "application/json", "X-Hub-Signature-256": sig})
            self.assertEqual(r.status_code, 200)

    def test_without_an_app_secret_the_webhook_refuses(self):
        with mock.patch.object(settings, "meta_app_secret", ""):
            self.assertEqual(self.post(payload()).status_code, 503)

    # --- receiving ---
    def test_message_is_logged_once_even_if_meta_retries(self):
        self.assertEqual(self.post(payload("wamid.X", "Hi there")).status_code, 200)
        self.assertEqual(self.post(payload("wamid.X", "Hi there")).status_code, 200)
        self.db.expire_all()
        msgs = self.db.scalars(select(WaMessage)).all()
        self.assertEqual(len(msgs), 1)
        conv = self.db.scalar(select(WaConversation))
        self.assertEqual((conv.wa_phone, conv.contact_name, conv.unread_count), (PHONE, "Ravi", 1))
        self.assertEqual(conv.last_message_preview, "Hi there")

    def test_message_for_another_number_is_ignored(self):
        self.post(payload(number_id="999"))
        self.assertIsNone(self.db.scalar(select(WaMessage.id)))

    def test_every_verified_call_is_saved_as_an_event(self):
        self.post(payload())
        self.db.expire_all()
        self.assertEqual(self.db.scalar(select(WaWebhookEvent.processed)), True)

    def test_stop_marks_the_customer_as_opted_out(self):
        self.post(payload("wamid.S", "STOP"))
        self.db.expire_all()
        self.assertTrue(self.db.scalar(select(WaConversation.opted_out)))

    # --- sending ---
    def _reply(self, conv_id, text="Thanks, checking"):
        return self.client.post(f"/api/whatsapp/conversations/{conv_id}/reply", json={"text": text}, headers=self.h(self.admin))

    def test_reply_inside_the_window_is_sent_and_logged(self):
        self.post(payload())
        cid = self.db.scalar(select(WaConversation.id))
        fake = mock.Mock(ok=True, content=b"x", text="")
        fake.json.return_value = {"messages": [{"id": "wamid.OUT1"}]}
        with mock.patch("app.services.whatsapp_inbox.requests.post", return_value=fake) as post:
            r = self._reply(cid)
        self.assertEqual(r.status_code, 200, r.text)
        self.assertEqual(post.call_count, 1)
        self.assertEqual(post.call_args.kwargs["json"]["to"], PHONE)
        self.db.expire_all()
        out = self.db.scalar(select(WaMessage).where(WaMessage.direction == "out"))
        self.assertEqual((out.status, out.wa_message_id, out.sent_by), ("sent", "wamid.OUT1", self.admin.id))

    def test_reply_after_24_hours_is_blocked_and_nothing_is_sent(self):
        old = int((datetime.now(timezone.utc) - timedelta(hours=30)).timestamp())
        self.post(payload(ts=old))
        cid = self.db.scalar(select(WaConversation.id))
        with mock.patch("app.services.whatsapp_inbox.requests.post") as post:
            r = self._reply(cid)
        self.assertEqual(r.status_code, 409)
        self.assertIn("24 hours", r.json()["detail"])
        post.assert_not_called()

    def test_reply_to_an_opted_out_number_is_blocked(self):
        self.post(payload("wamid.S", "stop"))
        cid = self.db.scalar(select(WaConversation.id))
        with mock.patch("app.services.whatsapp_inbox.requests.post") as post:
            self.assertEqual(self._reply(cid).status_code, 409)
        post.assert_not_called()

    def test_failed_send_is_recorded_not_retried(self):
        self.post(payload())
        cid = self.db.scalar(select(WaConversation.id))
        fake = mock.Mock(ok=False, content=b"x", text="boom")
        fake.json.return_value = {"error": {"message": "Token expired"}}
        with mock.patch("app.services.whatsapp_inbox.requests.post", return_value=fake) as post:
            r = self._reply(cid)
        self.assertEqual(r.status_code, 409)
        self.assertEqual(post.call_count, 1)
        self.db.expire_all()
        self.assertEqual(self.db.scalar(select(WaMessage.status).where(WaMessage.direction == "out")), "failed")

    # --- delivery status ---
    def test_status_only_moves_forward(self):
        self.post(payload())
        cid = self.db.scalar(select(WaConversation.id))
        fake = mock.Mock(ok=True, content=b"x", text="")
        fake.json.return_value = {"messages": [{"id": "wamid.OUT2"}]}
        with mock.patch("app.services.whatsapp_inbox.requests.post", return_value=fake):
            self._reply(cid)
        self.post(status_payload("wamid.OUT2", "delivered"))
        self.post(status_payload("wamid.OUT2", "sent"))  # arrives late: must not undo "delivered"
        self.db.expire_all()
        self.assertEqual(self.db.scalar(select(WaMessage.status).where(WaMessage.wa_message_id == "wamid.OUT2")), "delivered")
        self.post(status_payload("wamid.OUT2", "read"))
        self.db.expire_all()
        self.assertEqual(self.db.scalar(select(WaMessage.status).where(WaMessage.wa_message_id == "wamid.OUT2")), "read")

    # --- permissions ---
    def test_inbox_needs_the_whatsapp_permission(self):
        self.post(payload())
        self.assertEqual(self.client.get("/api/whatsapp/conversations", headers=self.h(self.eng)).status_code, 403)
        self.assertEqual(self.client.get("/api/whatsapp/conversations").status_code, 401)
        r = self.client.get("/api/whatsapp/conversations", headers=self.h(self.admin))
        self.assertEqual(r.status_code, 200, r.text)
        self.assertEqual(r.json()["total"], 1)

    def test_open_thread_marks_context_and_read(self):
        self.post(payload())
        cid = self.db.scalar(select(WaConversation.id))
        d = self.client.get(f"/api/whatsapp/conversations/{cid}", headers=self.h(self.admin)).json()
        self.assertEqual(len(d["messages"]), 1)
        self.assertTrue(d["conversation"]["window_open"])
        self.client.post(f"/api/whatsapp/conversations/{cid}/read", headers=self.h(self.admin))
        self.db.expire_all()
        self.assertEqual(self.db.scalar(select(WaConversation.unread_count)), 0)


if __name__ == "__main__":
    unittest.main()
