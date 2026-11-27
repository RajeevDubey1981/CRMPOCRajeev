from __future__ import annotations

import hashlib
import hmac
import json
import os
import sys
import time
import unittest
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
from unittest import mock

os.environ.setdefault("MYSQL_DATABASE_URL", "sqlite://")
os.environ["SARVAM_API_KEY"] = "test-key"
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from fastapi.testclient import TestClient
from sqlalchemy import create_engine, select
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.config import settings
from app.database import Base, get_db
from app.main import app
from app.models import User
from app.models.call import Call
from app.models.complaint import Complaint
from app.models.whatsapp import WaAiRun, WaConversation, WaMessage, WaNote
from app.routers import sarvam_api
from app.security import create_access_token, hash_password
from app.seed import seed_roles
from app.services import wa_ai
from app.services.sarvam_chat import SarvamChatError

PHONE = "919891572565"


class AutoReplyTests(unittest.TestCase):
    def setUp(self):
        self._patches = [
            mock.patch.object(settings, "meta_app_secret", "s"),
            mock.patch.object(settings, "wa_phone_number_id", "111"),
            mock.patch.object(settings, "wa_access_token", "tok"),
            mock.patch.object(settings, "whatsapp_enabled", True),
            mock.patch.object(settings, "whatsapp_ai_enabled", True),
            mock.patch.object(settings, "sarvam_chat_api_key", "k"),
            mock.patch.object(sarvam_api.threading, "Thread"),
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
        wa_ai.set_switch(self.db, True, self.admin.id)
        self.conv = WaConversation(wa_phone=PHONE, contact_name="Ravi", status="open", last_inbound_at=datetime.now(timezone.utc))
        self.db.add(self.conv)
        self.db.commit()
        self.sent: list[str] = []
        self.counter = 0

        def fake_post(url, headers=None, json=None, timeout=None):
            self.counter += 1
            self.sent.append(json["text"]["body"])
            r = mock.Mock(ok=True, content=b"x", text="")
            r.json.return_value = {"messages": [{"id": f"wamid.OUT{self.counter}"}]}
            return r

        self._post = mock.patch("app.services.whatsapp_inbox.requests.post", side_effect=fake_post)
        self._post.start()

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
        self._post.stop()
        self.db.close()
        for p in self._patches:
            p.stop()

    def incoming(self, text, wa_id=None):
        m = WaMessage(conversation_id=self.conv.id, direction="in", wa_message_id=wa_id or f"wamid.IN{time.time_ns()}", msg_type="text",
                      body=text, status="received", created_at=datetime.now(timezone.utc))
        self.db.add(m)
        self.db.commit()
        return m

    def model(self, **obj):
        base = {"reply": "Hello Ravi", "action": "none", "comp_no": None, "name": None, "problem": None, "email": None,
                "query_type": None, "handoff_reason": None}
        base.update(obj)
        return mock.patch("app.services.wa_ai.chat_json", return_value=(base, 123))

    def run_msg(self, m):
        self.db.expire_all()
        return wa_ai.run_for_message(self.db, m.id)

    def conv_now(self):
        self.db.expire_all()
        return self.db.get(WaConversation, self.conv.id)

    # --- the gates ---
    def test_switch_off_means_no_reply(self):
        wa_ai.set_switch(self.db, False, self.admin.id)
        m = self.incoming("hi")
        with self.model() as chat:
            self.assertEqual(self.run_msg(m), "blocked")
        chat.assert_not_called()
        self.assertEqual(self.sent, [])

    def test_server_not_allowing_means_no_reply(self):
        with mock.patch.object(settings, "whatsapp_ai_enabled", False):
            self.assertEqual(self.run_msg(self.incoming("hi")), "blocked")
        self.assertEqual(self.sent, [])

    def test_staff_pause_handoff_closed_optout_each_stop_it(self):
        for change in ({"assigned_to": self.admin.id}, {"ai_paused": True}, {"status": "needs_staff"}, {"status": "closed"}, {"opted_out": True}):
            self.db.expire_all()
            c = self.db.get(WaConversation, self.conv.id)
            for k, v in {"assigned_to": None, "ai_paused": False, "status": "open", "opted_out": False}.items():
                setattr(c, k, v)
            for k, v in change.items():
                setattr(c, k, v)
            self.db.commit()
            with self.model():
                self.assertEqual(self.run_msg(self.incoming("hi")), "blocked", change)
        self.assertEqual(self.sent, [])

    # --- replying ---
    def test_a_reply_is_sent_once_even_if_the_message_is_processed_twice(self):
        m = self.incoming("Do you install ACs?")
        with self.model(reply="Yes, we do. Which city are you in?"):
            self.assertEqual(self.run_msg(m), "replied")
            self.assertEqual(self.run_msg(m), "skipped")
        self.assertEqual(self.sent, ["Yes, we do. Which city are you in?"])
        self.assertEqual(self.db.scalar(select(WaAiRun.outcome)), "replied")

    def test_an_older_message_is_not_answered_when_a_newer_one_arrived(self):
        old = self.incoming("one")
        self.incoming("two")
        with self.model():
            self.run_msg(old)
        self.assertEqual(self.sent, [])

    def test_a_reply_is_dropped_if_staff_take_over_while_the_model_is_thinking(self):
        m = self.incoming("hi")

        def slow(*a, **k):
            c = self.Session().get(WaConversation, self.conv.id)
            s = self.Session()
            c = s.get(WaConversation, self.conv.id)
            c.assigned_to = self.admin.id
            s.commit()
            return ({"reply": "late answer", "action": "none"}, 5)

        with mock.patch("app.services.wa_ai.chat_json", side_effect=slow):
            self.run_msg(m)
        self.assertEqual(self.sent, [])

    # --- handoff and safety ---
    def test_handoff_marks_the_chat_and_leaves_a_note(self):
        m = self.incoming("I want a refund")
        with self.model(action="handoff", reply="A team member will reply.", handoff_reason="refund request"):
            self.assertEqual(self.run_msg(m), "handoff")
        self.assertEqual(self.conv_now().status, "needs_staff")
        self.assertEqual(self.sent, ["A team member will reply."])
        self.assertIn("refund request", self.db.scalar(select(WaNote.body)))

    def test_hazard_words_skip_the_model_and_go_to_staff(self):
        m = self.incoming("my AC is sparking and smoke is coming")
        with self.model() as chat:
            self.assertEqual(self.run_msg(m), "handoff")
        chat.assert_not_called()
        self.assertIn("switch off", self.sent[0])
        self.assertEqual(self.conv_now().status, "needs_staff")

    def test_a_model_failure_goes_to_staff_with_a_holding_message(self):
        m = self.incoming("hello")
        with mock.patch("app.services.wa_ai.chat_json", side_effect=SarvamChatError("boom")):
            self.assertEqual(self.run_msg(m), "error")
        self.assertEqual(self.conv_now().status, "needs_staff")
        self.assertEqual(len(self.sent), 1)

    def test_too_many_automatic_replies_hand_over_to_staff(self):
        for i in range(wa_ai.settings.whatsapp_ai_hourly_limit):
            self.db.add(WaMessage(conversation_id=self.conv.id, direction="out", msg_type="text", body="x", status="sent", sent_by=None, created_at=datetime.now(timezone.utc)))
        self.db.commit()
        m = self.incoming("again")
        with self.model() as chat:
            self.assertEqual(self.run_msg(m), "handoff")
        chat.assert_not_called()

    # --- complaint status ---
    def _complaint(self, mobile, no):
        c = Complaint(comp_no=no, comp_date=date.today(), customer_name="N", customer_mobile=mobile, query_type="Service", status="Pending", access_code="1")
        self.db.add(c)
        self.db.commit()

    def test_status_is_looked_up_only_for_the_senders_own_number(self):
        self._complaint("9891572565", "IDC_MINE_1")
        self._complaint("9000000000", "IDC_OTHERS_9")
        with self.model(action="track_complaint", comp_no=None):
            self.run_msg(self.incoming("status?"))
        self.assertIn("IDC_MINE_1", self.sent[-1])
        self.assertNotIn("IDC_OTHERS_9", self.sent[-1])
        with self.model(action="track_complaint", comp_no="IDC_OTHERS_9"):
            self.run_msg(self.incoming("what about IDC_OTHERS_9"))
        self.assertNotIn("IDC_OTHERS_9", self.sent[-1])
        self.assertIn("could not find", self.sent[-1])

    # --- registering ---
    def test_a_complaint_is_registered_only_after_the_customer_says_yes(self):
        details = dict(action="register_complaint", name="Ravi Kumar", problem="AC is not cooling", email="ravi@example.com", query_type="Service", model="IDCACSBF18K3F 1.5 ton split", address="12 MG Road, Noida 201301", error_code="E6")
        with self.model(**details):
            self.run_msg(self.incoming("please register my AC problem, email ravi@example.com"))
        self.assertIn("Reply YES", self.sent[-1])
        self.assertEqual(self.db.query(Complaint).count(), 0)
        with self.model() as chat:
            self.run_msg(self.incoming("YES"))
        chat.assert_not_called()
        self.db.expire_all()
        complaints = self.db.query(Complaint).all()
        self.assertEqual(len(complaints), 1)
        c = complaints[0]
        self.assertEqual((c.customer_mobile, c.customer_email, c.query_type), ("9891572565", "ravi@example.com", "Service"))
        self.assertIn(c.comp_no, self.sent[-1])
        self.assertEqual(self.db.query(Call).count(), 0)  # a WhatsApp chat is not a voice call
        self.assertIsNone(self.conv_now().pending_action)

    def test_a_service_request_without_model_or_pin_is_not_registered_yet(self):
        details = dict(action="register_complaint", name="Ravi Kumar", problem="AC shows E6", email="ravi@example.com", query_type="Service", model=None, address="Noida", reply="What is your AC model and full address with PIN code?")
        with self.model(**details):
            self.run_msg(self.incoming("my AC shows E6"))
        self.assertNotIn("Reply YES", self.sent[-1])
        self.assertIsNone(self.conv_now().pending_action)

    def test_the_registered_complaint_keeps_model_address_and_error_code(self):
        details = dict(action="register_complaint", name="Ravi Kumar", problem="AC shows E6", email="ravi@example.com", query_type="Service", model="IDCACSBF18K3F", address="12 MG Road, Noida 201301", error_code="E6")
        with self.model(**details):
            self.run_msg(self.incoming("register it"))
        self.assertIn("E6", self.sent[-1])
        self.assertIn("201301", self.sent[-1])
        with self.model():
            self.run_msg(self.incoming("YES"))
        self.db.expire_all()
        c = self.db.query(Complaint).one()
        self.assertIn("201301", c.customer_address or "")
        self.assertIn("IDCACSBF18K3F", c.model_details or "")
        self.assertIn("E6", c.remark or "")

    def test_the_prompt_carries_the_support_agent_playbook(self):
        for needle in ("Error codes", "Registering a service request", "Tracking", "Close politely"):
            self.assertIn(needle, wa_ai.SYSTEM_PROMPT)

    def test_saying_no_registers_nothing(self):
        details = dict(action="register_complaint", name="Ravi Kumar", problem="AC is not cooling", email="ravi@example.com", query_type="Service", model="IDCACSBF18K3F 1.5 ton split", address="12 MG Road, Noida 201301", error_code="E6")
        with self.model(**details):
            self.run_msg(self.incoming("register it"))
        self.run_msg(self.incoming("No"))
        self.assertEqual(self.db.query(Complaint).count(), 0)
        self.assertIsNone(self.conv_now().pending_action)

    def test_missing_details_are_asked_for_not_registered(self):
        with self.model(action="register_complaint", name="Ravi", problem="AC not cooling", email=None, query_type="Service", reply="What is your email?"):
            self.run_msg(self.incoming("register my AC problem"))
        self.assertEqual(self.sent[-1], "What is your email?")
        self.assertEqual(self.db.query(Complaint).count(), 0)
        self.assertIsNone(self.conv_now().pending_action)

    # --- persona and auto-resume ---
    def test_the_assistant_introduces_itself_as_shubh_from_indcool_support(self):
        self.assertIn("Hi, I'm Shubh from INDcool Support.", wa_ai.SYSTEM_PROMPT)
        self.assertIn("Never claim to be a human", wa_ai.SYSTEM_PROMPT)

    def test_the_prompt_tells_it_to_list_matching_models_instead_of_asking_for_a_model_code(self):
        self.assertIn("do NOT start by asking for a model code", wa_ai.SYSTEM_PROMPT)
        self.assertIn("Never repeat a question", wa_ai.SYSTEM_PROMPT)

    def _staff_reply(self, hours_ago):
        self.db.add(WaMessage(conversation_id=self.conv.id, direction="out", msg_type="text", body="staff", status="sent",
                              sent_by=self.admin.id, created_at=datetime.now(timezone.utc) - timedelta(hours=hours_ago)))
        c = self.conv_now()
        c.assigned_to = self.admin.id
        self.db.commit()

    def test_a_chat_goes_back_to_automatic_replies_after_8_quiet_hours_when_that_is_switched_on(self):
        self._staff_reply(9)
        with mock.patch.object(settings, "whatsapp_ai_resume_hours", 8), self.model(reply="Back with you"):
            self.assertEqual(self.run_msg(self.incoming("hello again")), "replied")
        c = self.conv_now()
        self.assertIsNone(c.assigned_to)
        self.assertEqual(self.sent[-1], "Back with you")

    def test_by_default_a_chat_staff_answered_stays_with_staff_even_after_a_day(self):
        self._staff_reply(30)
        with self.model() as chat:
            self.assertEqual(self.run_msg(self.incoming("hello again")), "blocked")
        chat.assert_not_called()
        self.assertEqual(self.conv_now().assigned_to, self.admin.id)

    def test_taking_a_chat_without_replying_is_never_given_back_by_the_clock(self):
        c = self.conv_now()
        c.assigned_to = self.admin.id
        self.db.commit()
        with self.model():
            self.assertEqual(self.run_msg(self.incoming("hi")), "blocked")

    def test_an_old_handoff_with_a_staff_reply_reopens_the_chat(self):
        self._staff_reply(10)
        c = self.conv_now()
        c.status = "needs_staff"
        self.db.commit()
        with mock.patch.object(settings, "whatsapp_ai_resume_hours", 8), self.model(reply="Hello"):
            self.run_msg(self.incoming("anyone there?"))
        self.assertEqual(self.conv_now().status, "open")

    # --- breakage must never mean silence ---
    def test_a_missing_knowledge_table_falls_back_to_the_files(self):
        with mock.patch("app.services.wa_knowledge._from_db_unsafe", side_effect=RuntimeError("table is gone")):
            from app.services import wa_knowledge
            self.assertIn("1800 119 515", wa_knowledge.for_query("hello", self.db))

    def test_an_unexpected_crash_hands_the_chat_to_staff_with_a_holding_message(self):
        m = self.incoming("hello")
        self.db.expire_all()
        with mock.patch("app.services.wa_ai.chat_json", side_effect=RuntimeError("something odd")):
            try:
                wa_ai.run_for_message(self.db, m.id)
            except RuntimeError:
                wa_ai._recover(self.db, m.id)
        self.assertEqual(self.conv_now().status, "needs_staff")
        self.assertEqual(len(self.sent), 1)

    # --- tied into the CRM ---
    def _alerts(self, active_only=True):
        from app.models.pending_action import UserPendingAction

        self.db.expire_all()
        q = select(UserPendingAction).where(UserPendingAction.module == "whatsapp")
        rows = self.db.scalars(q).all()
        return [r for r in rows if r.is_active] if active_only else rows

    def test_a_handoff_raises_a_bell_alert_for_staff_and_a_reply_clears_it(self):
        m = self.incoming("I want a refund")
        with self.model(action="handoff", reply="A team member will reply.", handoff_reason="refund request"):
            self.run_msg(m)
        alerts = self._alerts()
        self.assertTrue(alerts)
        self.assertIn(self.admin.id, {a.recipient_user_id for a in alerts})
        self.assertIn(f"/whatsapp?conv={self.conv.id}", alerts[0].href)
        r = self.client.post(f"/api/whatsapp/conversations/{self.conv.id}/reply", json={"text": "Hello, I am on it"}, headers=self.h(self.admin))
        self.assertEqual(r.status_code, 200, r.text)
        self.assertEqual(self._alerts(), [])

    def test_resuming_or_closing_a_chat_also_clears_the_alert(self):
        m = self.incoming("refund please")
        with self.model(action="handoff", reply="Team will reply.", handoff_reason="refund"):
            self.run_msg(m)
        self.assertTrue(self._alerts())
        self.client.post(f"/api/whatsapp/conversations/{self.conv.id}/status", json={"status": "closed"}, headers=self.h(self.admin))
        self.assertEqual(self._alerts(), [])

    def test_a_registered_complaint_carries_the_customers_words_and_the_chat_gets_a_note(self):
        details = dict(action="register_complaint", name="Ravi Kumar", problem="AC is not cooling", email="ravi@example.com", query_type="Service", model="IDCACSBF18K3F 1.5 ton split", address="12 MG Road, Noida 201301", error_code="E6")
        with self.model(**details):
            self.run_msg(self.incoming("my split AC is not cooling at all"))
        with self.model():
            self.run_msg(self.incoming("YES"))
        self.db.expire_all()
        c = self.db.query(Complaint).one()
        self.assertIn("WhatsApp chat, customer wrote", c.remark)
        self.assertIn("my split AC is not cooling at all", c.remark)
        notes = [n.body for n in self.db.query(WaNote).all()]
        self.assertTrue(any(c.comp_no in n for n in notes))

    def test_the_complaint_page_can_find_the_customers_chat(self):
        self._complaint("9891572565", "IDC_LINK_1")
        self.db.expire_all()
        cid = self.db.query(Complaint).one().id
        r = self.client.get(f"/api/whatsapp/for-complaint/{cid}", headers=self.h(self.admin)).json()
        self.assertEqual(r["conversation_id"], self.conv.id)
        self.assertEqual(self.client.get(f"/api/whatsapp/for-complaint/{cid}", headers=self.h(self.eng)).json()["conversation_id"], None)
        self._complaint("9000000000", "IDC_LINK_2")
        other = self.db.query(Complaint).filter(Complaint.comp_no == "IDC_LINK_2").one().id
        self.assertIsNone(self.client.get(f"/api/whatsapp/for-complaint/{other}", headers=self.h(self.admin)).json()["conversation_id"])

    # --- wiring ---
    def test_a_new_incoming_message_is_handed_to_the_engine_once(self):
        body = {"entry": [{"changes": [{"field": "messages", "value": {
            "metadata": {"phone_number_id": "111"}, "contacts": [{"wa_id": PHONE, "profile": {"name": "Ravi"}}],
            "messages": [{"from": PHONE, "id": "wamid.NEW1", "timestamp": str(int(time.time())), "type": "text", "text": {"body": "hi"}}]}}]}]}
        raw = json.dumps(body).encode()
        sig = "sha256=" + hmac.new(b"s", raw, hashlib.sha256).hexdigest()
        with mock.patch("app.services.wa_ai.schedule") as sched:
            for _ in range(2):
                r = self.client.post("/api/whatsapp/webhook", content=raw, headers={"Content-Type": "application/json", "X-Hub-Signature-256": sig})
                self.assertEqual(r.status_code, 200)
        self.assertEqual(sched.call_count, 1)

    def h(self, u):
        return {"Authorization": f"Bearer {create_access_token(subject=str(u.id), extra_claims={'role': u.role})}"}

    def test_only_an_admin_can_use_the_master_switch(self):
        self.assertEqual(self.client.post("/api/whatsapp/ai-switch", json={"on": False}, headers=self.h(self.eng)).status_code, 403)
        r = self.client.post("/api/whatsapp/ai-switch", json={"on": False}, headers=self.h(self.admin))
        self.assertEqual((r.status_code, r.json()["ai_switch"]), (200, False))
        with mock.patch.object(settings, "sarvam_chat_api_key", ""):
            self.assertEqual(self.client.post("/api/whatsapp/ai-switch", json={"on": True}, headers=self.h(self.admin)).status_code, 409)

    def test_resume_gives_the_chat_back(self):
        c = self.conv_now()
        c.assigned_to, c.status, c.ai_paused = self.admin.id, "needs_staff", True
        self.db.commit()
        r = self.client.post(f"/api/whatsapp/conversations/{self.conv.id}/resume", headers=self.h(self.admin))
        self.assertEqual(r.status_code, 200, r.text)
        c = self.conv_now()
        self.assertEqual((c.assigned_to, c.status, c.ai_paused), (None, "open", False))


if __name__ == "__main__":
    unittest.main()
