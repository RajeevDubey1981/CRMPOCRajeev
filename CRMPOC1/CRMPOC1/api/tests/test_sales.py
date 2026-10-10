from __future__ import annotations

import os
import sys
import unittest
from datetime import date, datetime, timedelta, timezone
from pathlib import Path

os.environ.setdefault("MYSQL_DATABASE_URL", "sqlite://")
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from fastapi.testclient import TestClient
from sqlalchemy import create_engine, inspect, select
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.database import Base, get_db
from app.main import app
from app.models import Complaint, PartnerRegistration, Permission, Role, User
from app.models.pending_action import UserPendingAction
from app.sales import leads as L
from app.sales import quotes as Q
from app.sales import rules
from app.sales.db import SalesBase, get_sales_db, use_factory
from app.sales.models import SalesLead, SalesProfile
from app.security import create_access_token, hash_password


def sqlite_engine():
    return create_engine("sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool)


class RulesTests(unittest.TestCase):
    def test_heat_follows_the_points(self):
        self.assertEqual(rules.suggest_heat({})[0], "cold")
        self.assertEqual(rules.suggest_heat({"quote": True})[0], "warm")
        self.assertEqual(rules.suggest_heat({"boss": True, "onboard": True, "greet": True}), ("warm", ["Spoke to the decision maker", "Onboarding process explained", "Greeting mail sent"], 5))
        self.assertEqual(rules.suggest_heat({"quote": True, "time15": True, "onboard": True})[0], "hot")
        self.assertEqual(rules.suggest_heat({"greet": True})[0], "cold")
        level, why, score = rules.suggest_heat({"quote": True, "time15": True, "budget": True})
        self.assertEqual((level, score), ("hot", 8))
        self.assertIn("Budget is confirmed", why)
        self.assertEqual(rules.suggest_heat({"quote": True, "stale": True})[0], "cold")

    def test_priority_points(self):
        lvl, why, score = rules.suggest_priority(value_lakh=30, closes_on=None, lead_type="retail", heat="cold", follow_up_late=False)
        self.assertEqual((lvl, score), ("high", 3))
        lvl, _w, _s = rules.suggest_priority(value_lakh=30, closes_on=date.today() + timedelta(days=1), lead_type="gem", heat="hot", follow_up_late=False)
        self.assertEqual(lvl, "urgent")
        lvl, _w, _s = rules.suggest_priority(value_lakh=0, closes_on=None, lead_type="retail", heat="cold", follow_up_late=False)
        self.assertEqual(lvl, "low")
        lvl, why, _s = rules.suggest_priority(value_lakh=8, closes_on=None, lead_type="export", heat="cold", follow_up_late=False, source="Alibaba.com")
        self.assertIn("Marketplace buyer is asking many suppliers", why)

    def test_type_from_the_words(self):
        d = rules.detect_lead_type
        self.assertEqual(d("30 ACs for the CSD canteen at Delhi Cantt"), "csd")
        self.assertEqual(d("GeM bid for 120 split ACs"), "gem")
        self.assertEqual(d("compressor and PCB needed"), "spare")
        self.assertEqual(d("hotel project, 12 cassette ACs"), "corp")
        self.assertEqual(d("need 2 split ACs for my home"), "retail")
        self.assertEqual(d("price FOB Mundra for Kenya"), "export")
        self.assertEqual(d("anything", "partner"), "dealer")
        self.assertEqual(d("anything", "alibaba"), "export")

    def test_gst_default(self):
        self.assertEqual(rules.default_gst_for_hsn("8415"), 28)
        self.assertEqual(rules.default_gst_for_hsn("8418"), 18)

    def test_locked_ticks_are_not_in_the_defaults(self):
        for role in rules.TICK_DEFAULTS.values():
            self.assertFalse(role & rules.LOCKED_TICKS)
        self.assertEqual(rules.LOCKED_TICKS, {"approve_high", "override"})

    def test_phone_normal_form(self):
        self.assertEqual(L.norm_phone("98100 11223"), "9810011223")
        self.assertEqual(L.norm_phone("+91 98100 11223"), "9810011223")
        self.assertEqual(L.norm_phone("919810011223"), "9810011223")
        self.assertEqual(L.norm_phone("+977 98510 22334"), "+9779851022334")


from sales_base import SalesTestBase


class SalesApiTests(SalesTestBase):
    # ---------------- the two databases stay apart ----------------
    def test_no_table_is_shared(self):
        main_tables = set(inspect(self.main_engine).get_table_names())
        sales_tables = set(inspect(self.sales_engine).get_table_names())
        self.assertFalse(main_tables & sales_tables)
        self.assertTrue(all(t.startswith("sales_") for t in sales_tables))
        self.assertFalse([t for t in main_tables if t.startswith("sales_")])
        # no foreign key from the Sales tables into the CRM tables
        insp = inspect(self.sales_engine)
        for t in sales_tables:
            for fk in insp.get_foreign_keys(t):
                self.assertTrue(fk["referred_table"].startswith("sales_"), (t, fk))

    def test_switched_off_when_the_database_is_not_set_up(self):
        use_factory(None, None)
        r = self.get("/api/auth/me", self.admin)
        perm = [p for p in r.json()["permissions"] if p["module"] == "sales"][0]
        self.assertFalse(perm["can_view"])
        app.dependency_overrides.pop(get_sales_db)
        r = self.get("/api/sales/status", self.admin)
        self.assertEqual(r.status_code, 503)

    # ---------------- access ----------------
    def test_menu_tick_and_role_defaults(self):
        me = self.get("/api/auth/me", self.amit).json()
        self.assertTrue([p for p in me["permissions"] if p["module"] == "sales"][0]["can_view"])
        me = self.get("/api/auth/me", self.cc).json()
        self.assertFalse([p for p in me["permissions"] if p["module"] == "sales"][0]["can_view"])
        self.assertEqual(self.get("/api/sales/status", self.cc).status_code, 403)
        st = self.get("/api/sales/status", self.amit).json()
        self.assertIn("add_lead", st["ticks"])
        self.assertNotIn("see_all", st["ticks"])
        self.assertFalse(st["menu"]["leads_all"])
        st = self.get("/api/sales/status", self.karan).json()
        self.assertIn("see_all", st["ticks"])
        self.assertNotIn("override", st["ticks"])
        st = self.get("/api/sales/status", self.admin).json()
        self.assertEqual(set(st["ticks"]), set(rules.ALL_TICKS))
        self.assertEqual(set(self.get("/api/sales/status", self.sub).json()["ticks"]), set(rules.ALL_TICKS))

    def test_admin_ticks_a_role_and_a_person(self):
        self.assertEqual(self.post(f"/api/sales/leads", {"name": "x", "phone": "98100 11111"}, self.amit).status_code, 201)
        r = self.put("/api/sales/ticks/user/%d" % self.amit.id, {"ticks": {"upload": True, "add_lead": False}}, self.admin)
        self.assertEqual(r.status_code, 200, r.text)
        self.assertIn("upload", r.json()["ticks"])
        self.assertNotIn("add_lead", r.json()["ticks"])
        self.assertEqual(self.post("/api/sales/leads", {"name": "x", "phone": "98100 22222"}, self.amit).status_code, 403)
        # Pooja still follows the role
        self.assertIn("add_lead", self.get("/api/sales/status", self.pooja).json()["ticks"])
        # back to the role
        self.put("/api/sales/ticks/user/%d" % self.amit.id, {"ticks": {"upload": None, "add_lead": None}}, self.admin)
        self.assertIn("add_lead", self.get("/api/sales/status", self.amit).json()["ticks"])
        # a whole role
        self.put("/api/sales/ticks/role/team", {"ticks": {"team_dash": True}}, self.admin)
        self.assertIn("team_dash", self.get("/api/sales/status", self.pooja).json()["ticks"])
        self.put("/api/sales/ticks/role/team", {"ticks": {"team_dash": False}}, self.admin)
        self.assertNotIn("team_dash", self.get("/api/sales/status", self.pooja).json()["ticks"])
        hist = self.get("/api/sales/ticks/history", self.admin).json()
        self.assertTrue(any(h["tick"] == "upload" and h["person"] == "Amit Verma" for h in hist))

    def test_only_admin_changes_ticks_and_locked_ones_stay_locked(self):
        self.assertEqual(self.put("/api/sales/ticks/user/%d" % self.amit.id, {"ticks": {"upload": True}}, self.karan).status_code, 403)
        self.assertEqual(self.get("/api/sales/ticks", self.karan).status_code, 403)
        r = self.put("/api/sales/ticks/user/%d" % self.amit.id, {"ticks": {"override": True}}, self.admin)
        self.assertEqual(r.status_code, 400)
        r = self.put("/api/sales/ticks/role/mgr", {"ticks": {"approve_high": True}}, self.admin)
        self.assertEqual(r.status_code, 400)
        self.assertEqual(self.put("/api/sales/ticks/user/%d" % self.sub.id, {"ticks": {"upload": True}}, self.sub).status_code, 400)
        cat = self.get("/api/sales/ticks", self.admin).json()
        self.assertEqual({p["name"] for p in cat["people"]}, {"Amit Verma", "Pooja Singh", "Karan Malhotra"})

    # ---------------- registered first, then lead ----------------
    def test_first_sync_starts_from_now_then_enquiries_become_leads(self):
        self.complaint("IDC_OLD1", "Old Customer", "9000000001", "old enquiry")
        first = self.sync()
        self.assertTrue(first["started"])
        self.assertEqual(self.get("/api/sales/leads", self.karan).json()["total"], 0)
        self.complaint("IDC_NEW1", "Gupta Electricals", "98111 22334", "I need 20 split ACs 1.5 ton. Please send the price.")
        self.complaint("IDC_SERVICE", "Service Customer", "9000000002", "AC is not cooling", qtype="Service")
        stats = self.sync()
        self.assertEqual(stats["complaints"], 1)
        leads = self.get("/api/sales/leads", self.karan).json()["items"]
        self.assertEqual(len(leads), 1)
        lead = leads[0]
        self.assertEqual((lead["crm_ref"], lead["crm_kind"], lead["lead_type"]), ("IDC_NEW1", "complaint", "retail"))
        self.assertEqual(lead["owner_name"], "Amit Verma")  # handles retail in Uttar Pradesh
        self.assertEqual(lead["heat"], "warm")  # asked for the price
        self.assertTrue(lead["lead_no"].startswith("SL-"))
        self.assertIsNotNone(lead["first_call_minutes"])
        # the card in the owner's login popup, in the CRM database
        self.db.expire_all()
        cards = self.db.scalars(select(UserPendingAction).where(UserPendingAction.module == "sales")).all()
        self.assertEqual([c.recipient_user_id for c in cards], [self.amit.id])
        self.assertEqual(cards[0].href, f"/sales/leads/{lead['id']}")
        log = self.get("/api/sales/inbox-log", self.karan).json()
        self.assertIn("Registered, lead", log[0]["result"])
        # run again: nothing new, nothing doubled
        self.assertEqual(self.sync()["complaints"], 0)
        self.assertEqual(self.get("/api/sales/leads", self.karan).json()["total"], 1)

    def test_backfill_brings_in_recent_enquiries_on_request(self):
        self.complaint("IDC_B1", "Recent Customer", "9000000010", "wants a freezer")
        self.sync()
        self.assertEqual(self.get("/api/sales/leads", self.karan).json()["total"], 0)
        stats = self.sync(backfill_days=30)
        self.assertEqual(stats["complaints"], 1)

    def test_same_phone_is_one_lead(self):
        self.sync()
        self.complaint("IDC_D1", "Meena", "99110 55667", "deep freezer please send price")
        self.sync()
        self.complaint("IDC_D2", "Meena Traders", "+91 99110 55667", "delivery date please")
        stats = self.sync()
        self.assertEqual(stats["again"], 1)
        data = self.get("/api/sales/leads", self.karan).json()
        self.assertEqual(data["total"], 1)
        detail = self.get(f"/api/sales/leads/{data['items'][0]['id']}", self.karan).json()
        self.assertTrue(any("Asked again" in a["text"] for a in detail["activities"]))

    def test_each_person_sees_only_their_own_leads(self):
        a = self.new_lead(name="UP Customer", phone="98000 00001", state="Uttar Pradesh")
        b = self.new_lead(name="Rajasthan Bid", phone="98000 00002", state="Rajasthan", lead_type="gem", item="GeM bid for 10 ACs")
        self.assertEqual(a["owner_name"], "Amit Verma")
        self.assertEqual(b["owner_name"], "Pooja Singh")
        mine = self.get("/api/sales/leads", self.amit).json()
        self.assertEqual([x["name"] for x in mine["items"]], ["UP Customer"])
        self.assertEqual(self.get(f"/api/sales/leads/{b['id']}", self.amit).status_code, 404)
        self.assertEqual(self.get(f"/api/sales/leads/{b['id']}", self.pooja).status_code, 200)
        self.assertEqual(self.get("/api/sales/leads", self.karan).json()["total"], 2)

    def test_giving_leads(self):
        lead = self.new_lead(name="Nobody Fits", phone="98000 00003", state="Kerala", lead_type="dealer")
        self.assertIsNone(lead["owner_user_id"])
        self.assertEqual(self.post(f"/api/sales/leads/{lead['id']}/give", {"owner_user_id": self.pooja.id}, self.amit).status_code, 403)
        r = self.post(f"/api/sales/leads/{lead['id']}/give", {"owner_user_id": self.pooja.id}, self.karan)
        self.assertEqual(r.json()["owner_name"], "Pooja Singh")
        self.assertEqual(self.post(f"/api/sales/leads/{lead['id']}/give", {"owner_user_id": self.cc.id}, self.karan).status_code, 400)
        self.db.expire_all()
        self.assertTrue(self.db.scalars(select(UserPendingAction).where(UserPendingAction.recipient_user_id == self.pooja.id, UserPendingAction.module == "sales")).first())

    # ---------------- working a lead ----------------
    def test_call_rating_and_priority(self):
        lead = self.new_lead(state="Uttar Pradesh")
        lid = lead["id"]
        r = self.post(f"/api/sales/leads/{lid}/call", {"outcome": "Spoke: needs a quote", "note": "Wants it this month", "next_follow_up": date.today().isoformat(), "answers": {"quote": True, "time15": True, "boss": True}}, self.amit)
        self.assertEqual(r.status_code, 200, r.text)
        out = r.json()
        self.assertEqual(out["status"], "int")  # "needs a quote" means the lead is Interested
        self.assertEqual(out["heat"], "hot")
        self.assertIsNone(out["first_call_minutes"])
        # changing the suggestion needs a reason
        r = self.post(f"/api/sales/leads/{lid}/rate", {"answers": {"quote": True, "time15": True, "boss": True}, "heat": "cold"}, self.amit)
        self.assertEqual(r.status_code, 400)
        r = self.post(f"/api/sales/leads/{lid}/rate", {"answers": {"quote": True, "time15": True, "boss": True}, "heat": "warm", "why": "Customer is travelling"}, self.amit)
        self.assertEqual(r.json()["heat"], "warm")
        self.assertIn("Changed by Amit Verma", r.json()["heat_by"])
        # a team member can only flag High; the manager sets any level, with a reason when it differs
        self.assertEqual(self.post(f"/api/sales/leads/{lid}/priority", {"level": "urgent", "why": "x y z w v"}, self.amit).status_code, 403)
        self.assertEqual(self.post(f"/api/sales/leads/{lid}/priority", {"level": "urgent", "why": "x y z w v", "flag": True}, self.amit).status_code, 400)
        r = self.post(f"/api/sales/leads/{lid}/priority", {"level": "high", "why": "Will order if we reply today", "flag": True}, self.amit)
        self.assertEqual(r.json()["priority"], "high")
        self.assertEqual(self.post(f"/api/sales/leads/{lid}/priority", {"level": "urgent"}, self.karan).status_code, 400)
        r = self.post(f"/api/sales/leads/{lid}/priority", {"level": "urgent", "why": "Large order from a known buyer"}, self.karan)
        self.assertEqual(r.json()["priority"], "urgent")
        detail = self.get(f"/api/sales/leads/{lid}", self.amit).json()
        self.assertTrue(any(a["kind"] == "call" for a in detail["activities"]))
        self.assertTrue(any(a["kind"] == "priority" for a in detail["activities"]))

    # ---------------- disposal ----------------
    def test_disposal_won_closes_the_original_enquiry(self):
        self.sync()
        c = self.complaint("IDC_W1", "Gupta Electricals", "98111 22334", "20 split ACs please send price")
        self.sync()
        lead = self.get("/api/sales/leads", self.karan).json()["items"][0]
        r = self.post(f"/api/sales/leads/{lead['id']}/dispose", {"reason": "won", "note": "Order confirmed on the phone", "order_no": "PO-77"}, self.amit)
        self.assertEqual(r.json()["status"], "won")
        self.db.expire_all()
        self.assertEqual(self.db.get(Complaint, c.id).status, "Resolved")
        self.assertEqual(self.lead_row(lead["id"]).order_no, "PO-77")

    def test_lost_waits_for_the_manager_then_closes(self):
        self.sync()
        c = self.complaint("IDC_L1", "Arora Sales", "98180 70707", "200 split ACs price")
        self.sync()
        lead = self.get("/api/sales/leads", self.karan).json()["items"][0]
        self.assertEqual(self.post(f"/api/sales/leads/{lead['id']}/dispose", {"reason": "lost_price", "note": "short"}, self.amit).status_code, 400)
        r = self.post(f"/api/sales/leads/{lead['id']}/dispose", {"reason": "lost_price", "note": "Got Rs 3,000 less per unit elsewhere"}, self.amit)
        self.assertEqual(r.json()["status"], "rev")
        self.db.expire_all()
        self.assertEqual(self.db.get(Complaint, c.id).status, "Pending")  # not closed yet
        self.assertEqual(self.post(f"/api/sales/leads/{lead['id']}/disposal/approve", {}, self.amit).status_code, 403)
        r = self.post(f"/api/sales/leads/{lead['id']}/disposal/approve", {}, self.karan)
        self.assertEqual(r.json()["status"], "dis")
        self.db.expire_all()
        self.assertEqual(self.db.get(Complaint, c.id).status, "Rejected")
        # the manager can reopen
        r = self.post(f"/api/sales/leads/{lead['id']}/disposal/reopen", {}, self.karan)
        self.assertEqual(r.json()["status"], "int")

    def test_a_manager_closes_a_lost_lead_at_once(self):
        lead = self.new_lead()
        r = self.post(f"/api/sales/leads/{lead['id']}/dispose", {"reason": "wrong", "note": "Number is switched off, 5 attempts"}, self.karan)
        self.assertEqual(r.json()["status"], "dis")

    # ---------------- partner registration leads: papers and disposal come from the CRM ----------------
    def registration(self, no="PR-T-1", partner_type="Gem Partner", business="Private Limited", status_="In Progress", **kw):
        r = PartnerRegistration(
            registration_no=no, access_token=no + "-token", partner_type=partner_type, business_type=business, name="Shree Sales and Services",
            mobile="99280 61234", email="shree@t.com", form_status="In Progress", onboarding_status=status_, state="Rajasthan", city="Jaipur", gst_no="08AAAAA1234A1Z5",
            gst_certificate_path="a.pdf", pan_card_path="b.pdf", address_proof_path="c.pdf", shop_photo_1_path="s1.jpg", **kw,
        )
        self.db.add(r)
        self.db.commit()
        return r

    def test_partner_leads_show_the_crm_papers_and_are_closed_by_the_crm(self):
        self.sync()
        reg = self.registration()
        self.sync()
        data = self.get("/api/sales/leads", self.karan).json()
        lead = [x for x in data["items"] if x["crm_kind"] == "partner"][0]
        self.assertEqual((lead["lead_type"], lead["crm_ref"]), ("dealer", "PR-T-1"))
        detail = self.get(f"/api/sales/leads/{lead['id']}", self.karan).json()
        papers = {p["key"]: p for p in detail["partner"]["papers"]}
        self.assertTrue(papers["gst_certificate"]["ok"])
        self.assertFalse(papers["cancelled_cheque"]["ok"])
        self.assertTrue(papers["incorporation_certificate"]["required"])  # a Private Limited needs the deed
        self.assertIn("gem_seller_id", papers)  # a Gem Partner needs the GeM Seller ID
        self.assertEqual(detail["partner"]["required_done"], len([p for p in papers.values() if p["required"] and p["ok"]]))
        # a hand disposal is refused
        r = self.post(f"/api/sales/leads/{lead['id']}/dispose", {"reason": "noint", "note": "Not interested in the offer"}, self.karan)
        self.assertEqual(r.status_code, 400)
        self.assertIn("CRM", r.json()["detail"])
        # the CRM rejects: the lead stays open, back with the partner
        self.db.expire_all()
        reg = self.db.get(PartnerRegistration, reg.id)
        reg.onboarding_status, reg.admin_remark = "Rejected", "GST certificate is not readable"
        self.db.commit()
        d = self.get(f"/api/sales/leads/{lead['id']}", self.karan).json()
        self.assertEqual((d["status"], d["closed"]), ("con", False))
        # the CRM approves: Won, closed by the CRM, no manager approval
        reg = self.db.get(PartnerRegistration, reg.id)
        reg.onboarding_status = "Onboarding Approved"
        self.db.commit()
        d = self.get(f"/api/sales/leads/{lead['id']}", self.karan).json()
        self.assertEqual((d["status"], d["disposal_reason"], d["closed"]), ("won", "pr_won", True))

    def test_partner_cancelled_in_the_crm_closes_the_lead(self):
        self.sync()
        reg = self.registration("PR-T-2", partner_type="CSD Dealer", business="Proprietorship")
        self.sync()
        lead = [x for x in self.get("/api/sales/leads", self.karan).json()["items"] if x["crm_kind"] == "partner"][0]
        d = self.get(f"/api/sales/leads/{lead['id']}", self.karan).json()
        shop = [p for p in d["partner"]["papers"] if p["key"] == "shop_photos"][0]
        self.assertIn("1 of 5", shop["note"])
        self.assertFalse(shop["ok"])
        inc = [p for p in d["partner"]["papers"] if p["key"] == "incorporation_certificate"][0]
        self.assertFalse(inc["required"])  # a proprietor does not need the deed
        reg = self.db.get(PartnerRegistration, reg.id)
        reg.onboarding_status, reg.admin_remark = "Cancelled", "Partner is not interested"
        self.db.commit()
        d = self.get(f"/api/sales/leads/{lead['id']}", self.karan).json()
        self.assertEqual((d["status"], d["disposal_reason"]), ("dis", "pr_can"))
        self.assertIn("not interested", d["disposal_note"])

    def test_remind_and_ask_to_cancel(self):
        self.sync()
        self.registration("PR-T-3")
        self.sync()
        lead = [x for x in self.get("/api/sales/leads", self.karan).json()["items"] if x["crm_kind"] == "partner"][0]
        import app.services.email_service as email_service
        sent = []
        original = email_service.send_partner_registration_invite_email
        email_service.send_partner_registration_invite_email = lambda **kw: sent.append(kw) or True
        try:
            r = self.post(f"/api/sales/leads/{lead['id']}/partner/remind", {}, self.karan)
            self.assertEqual(r.status_code, 200, r.text)
            self.assertEqual(len(sent), 1)
            # the CRM allows one resend
            r = self.post(f"/api/sales/leads/{lead['id']}/partner/remind", {}, self.karan)
            self.assertEqual(r.status_code, 400)
            self.assertEqual(len(sent), 1)
        finally:
            email_service.send_partner_registration_invite_email = original
        r = self.post(f"/api/sales/leads/{lead['id']}/partner/cancel-request", {"reason": "Said no on the phone"}, self.karan)
        self.assertEqual(r.status_code, 200)
        self.assertGreaterEqual(r.json()["told"], 2)  # Admin and Sub Admin
        self.db.expire_all()
        cards = self.db.scalars(select(UserPendingAction).where(UserPendingAction.action_type == "sales_cancel_request")).all()
        self.assertEqual({c.recipient_user_id for c in cards}, {self.admin.id, self.sub.id})

    # ---------------- quotations ----------------
    def add_item(self, code="IDCACSBF16K5", name="Split AC 1.5 Ton 5 Star Inverter", hsn="8415", mrp=41500):
        from app.models.item_master import ItemMaster
        self.db.add(ItemMaster(item_code=code, item_name=name, hsn_code=hsn, mrp=mrp, is_active=True))
        self.db.commit()

    def test_quotation_gst_split_and_numbers(self):
        self.add_item()
        lead = self.new_lead(state="Uttar Pradesh")
        r = self.post(f"/api/sales/leads/{lead['id']}/quotations", {"items": [{"item_code": "IDCACSBF16K5", "qty": 20, "discount_pct": 3}]}, self.karan)
        self.assertEqual(r.status_code, 201, r.text)
        q = r.json()
        self.assertRegex(q["quote_no"], r"^QT/\d{4}-\d{2}/0001$")
        line = q["lines"][0]
        self.assertEqual((line["item_name"], line["hsn"], line["rate"], line["gst_pct"]), ("Split AC 1.5 Ton 5 Star Inverter", "8415", 41500.0, 28.0))
        self.assertEqual(q["gross"], 830000.0)
        self.assertEqual(q["taxable"], 805100.0)
        self.assertEqual(q["tax"], 225428.0)
        self.assertEqual(q["total"], 1030528.0)
        self.assertTrue(q["intra_state"])  # customer is in the home state
        # another state: IGST (same totals, not split)
        r = self.put(f"/api/sales/quotations/{q['id']}", {"state": "Bihar"}, self.karan)
        self.assertFalse(r.json()["intra_state"])
        self.assertEqual(r.json()["total"], 1030528.0)
        lead2 = self.new_lead(name="Second", phone="98000 00099")
        q2 = self.post(f"/api/sales/leads/{lead2['id']}/quotations", {"items": [{"item_name": "Fan", "qty": 1, "rate": 100, "gst_pct": 18}]}, self.karan).json()
        self.assertTrue(q2["quote_no"].endswith("/0002"))
        self.assertEqual(q2["company"]["address"], "OC528, Gaur City, Greater Noida West, Uttar Pradesh")

    def test_item_price_is_copied_onto_the_line(self):
        self.add_item()
        lead = self.new_lead()
        q = self.post(f"/api/sales/leads/{lead['id']}/quotations", {"items": [{"item_code": "IDCACSBF16K5", "qty": 1}]}, self.karan).json()
        from app.models.item_master import ItemMaster
        item = self.db.scalar(select(ItemMaster).where(ItemMaster.item_code == "IDCACSBF16K5"))
        item.mrp = 99999
        self.db.commit()
        again = self.get(f"/api/sales/quotations/{q['id']}", self.karan).json()
        self.assertEqual(again["lines"][0]["rate"], 41500.0)

    def test_approval_path_with_a_high_discount_and_override(self):
        self.add_item()
        lead = self.new_lead(state="Uttar Pradesh")
        lid = lead["id"]
        qid = self.post(f"/api/sales/leads/{lid}/quotations", {"items": [{"item_code": "IDCACSBF16K5", "qty": 10, "discount_pct": 14}]}, self.amit).json()["id"]
        # a high discount goes to Admin as well
        r = self.post(f"/api/sales/quotations/{qid}/submit", {}, self.amit)
        self.assertEqual(r.json()["status"], "wadm")
        self.assertEqual(self.post(f"/api/sales/quotations/{qid}/approve", {}, self.karan).status_code, 403)
        # a draft cannot be edited once submitted
        self.assertEqual(self.put(f"/api/sales/quotations/{qid}", {"note": "x"}, self.amit).status_code, 400)
        r = self.post(f"/api/sales/quotations/{qid}/return", {"reason": "Please reduce the discount"}, self.karan)
        self.assertEqual(r.json()["status"], "ret")
        r = self.put(f"/api/sales/quotations/{qid}", {"items": [{"item_code": "IDCACSBF16K5", "qty": 10, "discount_pct": 4}]}, self.amit)
        self.assertEqual(r.status_code, 200)
        self.assertFalse(r.json()["high_discount"])
        self.assertEqual(self.post(f"/api/sales/quotations/{qid}/submit", {}, self.amit).json()["status"], "wait")
        # the team member cannot approve; the manager can
        self.assertEqual(self.post(f"/api/sales/quotations/{qid}/approve", {}, self.amit).status_code, 403)
        r = self.post(f"/api/sales/quotations/{qid}/approve", {}, self.karan)
        self.assertEqual((r.json()["status"], r.json()["approved_by_name"]), ("appr", "Karan Malhotra"))
        r = self.post(f"/api/sales/quotations/{qid}/send", {}, self.amit)
        self.assertEqual(r.json()["status"], "sent")
        self.assertEqual(self.lead_row(lid).status, "quo")
        # only Admin cancels, and with a reason
        self.assertEqual(self.post(f"/api/sales/quotations/{qid}/cancel", {"reason": "Customer changed the order"}, self.karan).status_code, 403)
        self.assertEqual(self.post(f"/api/sales/quotations/{qid}/cancel", {}, self.admin).status_code, 400)
        r = self.post(f"/api/sales/quotations/{qid}/cancel", {"reason": "Customer changed the order"}, self.admin)
        self.assertEqual(r.json()["status"], "cancel")
        self.assertTrue(any("ADMIN OVERRIDE" in h["text"] for h in r.json()["history"]))

    def test_admin_approves_a_high_discount_and_can_override_a_rejection(self):
        self.add_item()
        lead = self.new_lead()
        qid = self.post(f"/api/sales/leads/{lead['id']}/quotations", {"items": [{"item_code": "IDCACSBF16K5", "qty": 5, "discount_pct": 15}]}, self.amit).json()["id"]
        self.post(f"/api/sales/quotations/{qid}/submit", {}, self.amit)
        r = self.post(f"/api/sales/quotations/{qid}/approve", {}, self.sub)
        self.assertEqual(r.json()["status"], "appr")
        lead2 = self.new_lead(name="Other", phone="98000 00055")
        qid2 = self.post(f"/api/sales/leads/{lead2['id']}/quotations", {"items": [{"item_code": "IDCACSBF16K5", "qty": 1}]}, self.amit).json()["id"]
        self.post(f"/api/sales/quotations/{qid2}/submit", {}, self.amit)
        self.assertEqual(self.post(f"/api/sales/quotations/{qid2}/reject", {"reason": "Price list is old"}, self.karan).json()["status"], "rej")
        self.assertEqual(self.post(f"/api/sales/quotations/{qid2}/approve", {}, self.karan).status_code, 403)
        self.assertEqual(self.post(f"/api/sales/quotations/{qid2}/approve", {}, self.admin).status_code, 400)  # a reason is needed
        self.assertEqual(self.post(f"/api/sales/quotations/{qid2}/approve", {"reason": "Customer is a key account"}, self.admin).json()["status"], "appr")

    def test_export_quotation_is_in_dollars_with_no_gst(self):
        self.add_item()
        lead = self.new_lead(name="Himalaya Cool Traders", phone="+977 98510 22334", lead_type="export", country="Nepal", state=None, place="Kathmandu", price_basis="DAP Birgunj")
        q = self.post(f"/api/sales/leads/{lead['id']}/quotations", {"items": [{"item_code": "IDCACSBF16K5", "qty": 200, "discount_pct": 2}]}, self.karan).json()
        self.assertEqual(q["currency"], "USD")
        self.assertEqual(q["state"], "Nepal")
        self.assertEqual(q["valid_days"], 30)
        self.assertEqual(q["tax"], 0.0)
        self.assertEqual(q["lines"][0]["gst_pct"], 0.0)
        self.assertAlmostEqual(q["lines"][0]["rate"], 471.59, places=2)  # 41,500 / 88
        self.assertIn("DAP Birgunj", q["delivery_terms"])
        self.assertEqual(q["total"], q["taxable"])

    def test_quotations_are_visible_to_their_makers_and_the_approvers(self):
        self.add_item()
        lead = self.new_lead(state="Uttar Pradesh")
        qid = self.post(f"/api/sales/leads/{lead['id']}/quotations", {"items": [{"item_code": "IDCACSBF16K5", "qty": 1}]}, self.amit).json()["id"]
        self.assertEqual(len(self.get("/api/sales/quotations", self.amit).json()), 1)
        self.assertEqual(self.get(f"/api/sales/quotations/{qid}", self.pooja).status_code, 404)
        self.assertEqual(len(self.get("/api/sales/quotations", self.karan).json()), 1)

    # ---------------- team, settings and the dashboard ----------------
    def test_profiles(self):
        r = self.put(f"/api/sales/team/{self.amit.id}/profile", {"pincode": "20130A"}, self.amit)
        self.assertEqual(r.status_code, 400)
        r = self.put(f"/api/sales/team/{self.amit.id}/profile", {"pincode": "201301", "state": "Uttar Pradesh", "district": "Gautam Buddha Nagar", "extra_pincodes": "110001,122001"}, self.amit)
        self.assertEqual(r.status_code, 200, r.text)
        self.assertEqual(r.json()["extra_pincodes"], ["110001", "122001"])
        # a member cannot change the types they handle, or anyone else
        self.assertEqual(self.put(f"/api/sales/team/{self.amit.id}/profile", {"types_handled": "gem"}, self.amit).status_code, 403)
        self.assertEqual(self.put(f"/api/sales/team/{self.pooja.id}/profile", {"state": "Rajasthan"}, self.amit).status_code, 403)
        self.assertEqual(self.put(f"/api/sales/team/{self.pooja.id}/profile", {"types_handled": "gem,bogus"}, self.karan).status_code, 400)
        self.assertEqual(self.put(f"/api/sales/team/{self.pooja.id}/profile", {"types_handled": "gem,tender,export", "target_lakh": 30}, self.karan).status_code, 200)
        team = self.get("/api/sales/team", self.amit).json()
        self.assertEqual([p["name"] for p in team], ["Amit Verma"])
        self.assertEqual(len(self.get("/api/sales/team", self.karan).json()), 3)
        self.assertEqual(self.put(f"/api/sales/team/{self.cc.id}/profile", {"state": "x"}, self.karan).status_code, 404)

    def test_settings(self):
        self.assertEqual(self.put("/api/sales/settings", {"fx_rate": 90}, self.amit).status_code, 403)
        self.assertEqual(self.put("/api/sales/settings", {"fx_rate": 90}, self.karan).status_code, 403)
        self.assertEqual(self.put("/api/sales/settings", {"fx_rate": 90, "discount_limit": 12}, self.admin).json()["fx_rate"], "90.0")
        self.put("/api/sales/ticks/user/%d" % self.karan.id, {"ticks": {"fx": True}}, self.admin)
        self.assertEqual(self.put("/api/sales/settings", {"fx_rate": 91}, self.karan).status_code, 200)
        self.assertEqual(self.put("/api/sales/settings", {"company_gstin": "09ABCDE1234F1Z5"}, self.karan).status_code, 403)

    def test_dashboard_scope_follows_the_ticks(self):
        self.new_lead(name="UP Customer", phone="98000 00001", state="Uttar Pradesh")
        self.new_lead(name="Rajasthan Bid", phone="98000 00002", state="Rajasthan", lead_type="gem", item="GeM bid")
        s = self.get("/api/sales/summary", self.amit).json()
        self.assertEqual(s["scope"], "mine")
        self.assertEqual({t["key"]: t["value"] for t in s["tiles"]}["open"], 1)
        tr = {t["key"]: t["trend"] for t in s["tiles"]}
        self.assertEqual(len(tr["open"]), 7)
        self.assertEqual(tr["open"][-1], 1)  # the lead was made today, the last of the seven days
        self.assertIsNone(s["target"])  # nobody has a month target yet
        self.put(f"/api/sales/team/{self.amit.id}/profile", {"target_lakh": 50}, self.admin)
        t = self.get("/api/sales/summary", self.amit).json()["target"]
        self.assertEqual((t["target_lakh"], t["won_lakh"]), (50.0, 0.0))
        self.assertGreaterEqual(t["days_left"], 1)
        s = self.get("/api/sales/summary", self.karan).json()
        self.assertEqual(s["scope"], "team")
        self.assertIn("leaderboard", s)
        s = self.get("/api/sales/summary", self.admin).json()
        self.assertEqual(s["scope"], "company")
        self.assertEqual({t["key"]: t["value"] for t in s["tiles"]}["new_today"], 2)
        # no dashboard tick, no numbers
        self.put("/api/sales/ticks/user/%d" % self.pooja.id, {"ticks": {"my_dash": False}}, self.admin)
        self.assertEqual(self.get("/api/sales/summary", self.pooja).status_code, 403)

    def test_list_filters(self):
        self.new_lead(name="Hot One", phone="98000 00011", state="Uttar Pradesh", message="urgent need, budget is ready, send price")
        self.new_lead(name="Cold One", phone="98000 00012", state="Uttar Pradesh", message="just asking")
        hot = self.get("/api/sales/leads?kpi=hot", self.karan).json()
        self.assertEqual([x["name"] for x in hot["items"]], ["Hot One"])
        self.assertEqual(self.get("/api/sales/leads?q=cold", self.karan).json()["total"], 1)
        self.assertEqual(self.get("/api/sales/leads?lead_type=gem", self.karan).json()["total"], 0)
        counts = self.get("/api/sales/leads", self.karan).json()["counts"]
        self.assertEqual((counts["all"], counts["hot"]), (2, 1))

    def test_auto_give_new_leads(self):
        for i, st in enumerate(("Uttar Pradesh", "Rajasthan")):
            L_lead = SalesLead(name=f"Pending {i}", phone=f"9800000{i}00", item="x", state=st, lead_type="retail" if i == 0 else "gem", status="new")
            self.sdb.add(L_lead)
        self.sdb.commit()
        r = self.post("/api/sales/leads-auto-give", {}, self.karan)
        self.assertEqual(r.json()["given"], 2)
        self.assertEqual(self.post("/api/sales/leads-auto-give", {}, self.amit).status_code, 403)


class MenuMigrationTests(unittest.TestCase):
    """0064 gives the CRM database a Sales Manager role and the Sales menu tick, and no Sales table."""

    def load(self):
        import importlib.util
        path = Path(__file__).resolve().parents[1] / "alembic" / "versions" / "0064_sales_menu.py"
        spec = importlib.util.spec_from_file_location("m0064", path)
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
        return mod

    def test_upgrade_is_safe_to_run_twice_and_downgrade_undoes_it(self):
        from alembic.migration import MigrationContext
        from alembic.operations import Operations

        engine = sqlite_engine()
        Base.metadata.create_all(engine)
        Session = sessionmaker(bind=engine, future=True)
        with Session() as db:
            roles = {n: Role(name=n, description=n) for n in ("admin", "sub_admin", "sales", "vendor")}
            db.add_all(roles.values())
            db.flush()
            db.add(Permission(role_id=roles["sales"].id, module="orders", can_view=True))
            db.add(Permission(role_id=roles["sales"].id, module="complaints", sub_module="Sales", can_view=True, can_edit=True))
            db.commit()
        mod = self.load()
        for _ in range(2):
            with engine.begin() as conn:
                with Operations.context(MigrationContext.configure(conn)):
                    mod.upgrade()
        with Session() as db:
            names = {r.name: r for r in db.scalars(select(Role))}
            self.assertIn("sales_manager", names)
            mgr = names["sales_manager"]
            copied = {(p.module, p.sub_module) for p in db.scalars(select(Permission).where(Permission.role_id == mgr.id))}
            self.assertEqual(copied, {("orders", None), ("complaints", "Sales"), ("sales", None)})
            for name in ("admin", "sub_admin", "sales", "sales_manager"):
                row = db.scalar(select(Permission).where(Permission.role_id == names[name].id, Permission.module == "sales"))
                self.assertTrue(row and row.can_view, name)
            self.assertIsNone(db.scalar(select(Permission).where(Permission.role_id == names["vendor"].id, Permission.module == "sales")))
            self.assertEqual(db.query(Permission).filter(Permission.module == "sales", Permission.role_id == names["sales_manager"].id).count(), 1)
        self.assertFalse([t for t in inspect(engine).get_table_names() if t.startswith("sales_")])
        with engine.begin() as conn:
            with Operations.context(MigrationContext.configure(conn)):
                mod.downgrade()
        with Session() as db:
            self.assertEqual(db.query(Permission).filter(Permission.module == "sales").count(), 0)
            self.assertIsNone(db.scalar(select(Role).where(Role.name == "sales_manager")))


if __name__ == "__main__":
    unittest.main()
