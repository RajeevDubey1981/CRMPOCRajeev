from __future__ import annotations

import os
import sys
import unittest
from datetime import date, timedelta
from pathlib import Path

os.environ.setdefault("MYSQL_DATABASE_URL", "sqlite://")
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from fastapi.testclient import TestClient
from sqlalchemy import create_engine, select
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.database import Base, get_db
from app.main import app
from app.models import Bid, BidEvent, BidReminder, BidRequest, Permission, Role, User, Vendor
from app.security import create_access_token, hash_password
from app.services import bid_service as svc


class DetectionTests(unittest.TestCase):
    def pick(self, text):
        r = svc.detect_category(text)
        return r["name"], r["type"]

    def test_categories_follow_the_website(self):
        self.assertEqual(self.pick("Split AC 1.5 ton 5 star, 120 units"), ("Residential Air Conditioners", "Split AC"))
        self.assertEqual(self.pick("Window AC 1.5 ton"), ("Residential Air Conditioners", "Window AC"))
        self.assertEqual(self.pick("Cassette air conditioner"), ("Residential Air Conditioners", "Cassette AC"))
        self.assertEqual(self.pick("Tower AC"), ("Residential Air Conditioners", "Tower AC"))
        self.assertEqual(self.pick("VRF AC system, 6 outdoor units"), ("Commercial Air Conditioners", "VRF AC"))
        self.assertEqual(self.pick("Ductable AC 5 TR"), ("Commercial Air Conditioners", "Ductable AC"))
        self.assertEqual(self.pick("Solar split AC"), ("Solar Air Conditioners", "Split AC"))
        self.assertEqual(self.pick("Single door refrigerator 190 litre"), ("Refrigerator", "Single Door"))
        self.assertEqual(self.pick("Double door fridge"), ("Refrigerator", "Double Door"))
        self.assertEqual(self.pick("Hard top deep freezer 300 litre"), ("Deep Freezer", "Hard Top"))
        self.assertEqual(self.pick("Front load washing machine"), ("Washing Machines", "Front Load"))
        self.assertEqual(self.pick("Water cooler, cold only"), ("Water Cooler", "Cold Only"))
        self.assertEqual(self.pick("Water cooler with RO UV"), ("Water Cooler", "All in one with RO (UV)"))
        self.assertEqual(self.pick("Vertical geyser 15 litre"), ("Geysers", "Vertical"))
        self.assertEqual(self.pick("Ceiling fan 1200 mm BLDC"), ("Fans", "Ceiling Fan"))
        self.assertEqual(self.pick("Exhaust fan"), ("Fans", "Exhaust Fan"))

    def test_air_cooler_is_other_appliances_and_unknown_is_flagged(self):
        self.assertEqual(self.pick("Desert air cooler 60 litre"), ("Other Appliances", "Air Cooler"))
        r = svc.detect_category("Office chairs")
        self.assertEqual((r["name"], r["type"], r["hit"]), ("Other Appliances", "Other", False))

    def test_tonnage_does_not_change_the_category(self):
        self.assertEqual(self.pick("Split AC 1.5 ton"), self.pick("Split AC 5 ton"))


class FuzzySearchTests(unittest.TestCase):
    NO = "GEM/2026/B/5821904 Split AC Residential"

    def test_finds(self):
        for q in ["5821904", "58", "9", "5821 904", "gem 2026 5821904", "GEM 2026 B 5821904", "5821904 gem",
                  "582l904", "5812904", "gem2026b5821", "2026 58", "g e m 5821"]:
            self.assertTrue(svc.fuzzy_match(q, self.NO), q)

    def test_ignores(self):
        for q in ["5855021", "5703345", "xyz", "9999999", "UPPWD", "1234567"]:
            self.assertFalse(svc.fuzzy_match(q, self.NO), q)

    def test_exact_number_ranks_first(self):
        self.assertEqual(svc.search_rank("5821904", "GEM/2026/B/5821904"), 0)
        self.assertEqual(svc.search_rank("5821904", "GEM/2026/B/5855021"), 1)


class BidApiTests(unittest.TestCase):
    def setUp(self):
        engine = create_engine("sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool)
        Base.metadata.create_all(engine)
        self.Session = sessionmaker(bind=engine, autoflush=False, autocommit=False, future=True)
        self.db = self.Session()

        def override():
            s = self.Session()
            try:
                yield s
            finally:
                s.close()

        app.dependency_overrides[get_db] = override
        self.client = TestClient(app)
        self.sent: list[tuple[str, str]] = []
        self._orig_send = svc._deliver
        svc._deliver = lambda to, subject, lines: (self.sent.append((to, subject)) or bool((to or "").strip()))

        vendor_role = Role(name="vendor", description="v")
        admin_role = Role(name="admin", description="a")
        self.db.add_all([vendor_role, admin_role])
        self.db.flush()
        self.db.add(Permission(role_id=vendor_role.id, module="bids", can_view=True, can_create=True, can_edit=True))
        self.db.add(Permission(role_id=admin_role.id, module="bids", can_view=True, can_create=True, can_edit=True, can_delete=True, can_export=True))
        self.admin = self._user("admin@t.com", "admin", "Admin")
        self.sub = self._user("sub@t.com", "sub_admin", "Sub")
        self.sales = self._user("sales@t.com", "sales", "Sales Tick", tick=True)
        self.sales_plain = self._user("sales2@t.com", "sales", "Sales Plain")
        self.v1, self.vu1 = self._vendor("V001", "Frost Point", "frost@t.com")
        self.v2, self.vu2 = self._vendor("V002", "Arctic Sales", "arctic@t.com")
        self.v3, self.vu3 = self._vendor("V003", "Cool Zone", "cool@t.com")
        self.db.commit()

    def tearDown(self):
        svc._deliver = self._orig_send
        app.dependency_overrides.clear()
        self.db.close()

    # helpers
    def _user(self, email, role, name, tick=False):
        u = User(name=name, email=email, password_hash=hash_password("pw123456"), role=role, is_active=True, can_manage_bids=tick)
        self.db.add(u)
        self.db.flush()
        return u

    def _vendor(self, code, name, email):
        v = Vendor(vendor_code=code, name_of_firm=name, email=email, is_active=True)
        self.db.add(v)
        self.db.flush()
        return v, self._user(email, "vendor", name)

    def h(self, user):
        return {"Authorization": f"Bearer {create_access_token(subject=str(user.id), extra_claims={'role': user.role})}"}

    def enter(self, number="GEM/2026/B/5821904", title="Split AC 1.5 ton, 120 units", days=10, **extra):
        today = svc.today_ist()
        body = {"bid_number": number, "bid_type": "GeM", "title": title, "end_date": (today + timedelta(days=days)).isoformat(),
                "publish_date": today.isoformat(), **extra}
        r = self.client.post("/api/bids", json=body, headers=self.h(self.sub))
        self.assertEqual(r.status_code, 201, r.text)
        return r.json()

    def allocate(self, bid_id, vendor, who=None, **body):
        return self.client.post(f"/api/bids/{bid_id}/allocate", json={"vendor_id": vendor.id, **body}, headers=self.h(who or self.sub))

    def bid(self, bid_id) -> Bid:
        self.db.expire_all()
        return self.db.get(Bid, bid_id)

    # --- access
    def test_access_rules(self):
        self.assertEqual(self.client.get("/api/bids", headers=self.h(self.sales_plain)).status_code, 403)
        self.assertEqual(self.client.get("/api/bids", headers=self.h(self.sales)).status_code, 200)
        self.assertEqual(self.client.get("/api/bids", headers=self.h(self.admin)).status_code, 200)
        self.assertEqual(self.client.get("/api/bids", headers=self.h(self.sub)).status_code, 200)
        self.assertEqual(self.client.get("/api/bids", headers=self.h(self.vu1)).status_code, 200)
        self.assertEqual(self.client.get("/api/bids").status_code, 401)

    def test_vendor_without_role_card_row_has_no_access(self):
        self.db.query(Permission).filter(Permission.module == "bids", Permission.role_id == self.db.scalar(select(Role.id).where(Role.name == "vendor"))).delete()
        self.db.commit()
        self.assertEqual(self.client.get("/api/bids", headers=self.h(self.vu1)).status_code, 403)

    def test_me_reports_bids_permission(self):
        def bids_perm(user):
            me = self.client.get("/api/auth/me", headers=self.h(user)).json()
            return next(p for p in me["permissions"] if p["module"] == "bids" and p["sub_module"] is None), me

        p, me = bids_perm(self.sales)
        self.assertTrue(p["can_view"] and p["can_create"] and not p["can_delete"])
        self.assertTrue(me["can_manage_bids"])
        p, _ = bids_perm(self.sales_plain)
        self.assertFalse(p["can_view"])
        p, _ = bids_perm(self.sub)
        self.assertTrue(p["can_view"] and p["can_delete"])
        p, _ = bids_perm(self.vu1)
        self.assertTrue(p["can_view"] and not p["can_edit"])

    def test_only_admin_side_sets_the_tick_and_never_on_a_vendor(self):
        r = self.client.put(f"/api/users/{self.sales_plain.id}", json={"can_manage_bids": True}, headers=self.h(self.admin))
        self.assertEqual(r.status_code, 200, r.text)
        self.assertTrue(r.json()["can_manage_bids"])
        r = self.client.put(f"/api/users/{self.sales_plain.id}", json={"can_manage_bids": True}, headers=self.h(self.sales))
        self.assertEqual(r.status_code, 403)
        r = self.client.put(f"/api/users/{self.vu1.id}", json={"can_manage_bids": True}, headers=self.h(self.admin))
        self.assertEqual(r.status_code, 200)
        self.assertFalse(r.json()["can_manage_bids"])

    # --- entering
    def test_enter_detects_category_and_rejects_duplicates(self):
        bid = self.enter(title="Hard top deep freezer 300 litre, 15 units", number="GEM/2026/B/5855021")
        self.assertEqual((bid["product_category"], bid["product_type"]), ("Deep Freezer", "Hard Top"))
        self.assertEqual(bid["status"], "Open")
        r = self.client.post("/api/bids", json={"bid_number": "gem 2026 b 5855021", "title": "x y", "end_date": "2030-01-01"}, headers=self.h(self.sub))
        self.assertEqual(r.status_code, 409)

    def test_enter_keeps_category_chosen_on_the_form(self):
        bid = self.enter(title="Anything", product_category="Fans", product_type="Exhaust Fan")
        self.assertEqual((bid["product_category"], bid["product_type"]), ("Fans", "Exhaust Fan"))

    def test_vendor_cannot_enter_a_bid(self):
        r = self.client.post("/api/bids", json={"bid_number": "GEM/1", "title": "ab", "end_date": "2030-01-01"}, headers=self.h(self.vu1))
        self.assertEqual(r.status_code, 403)

    # --- allocation, locks
    def test_allocate_locks_and_emails_vendor(self):
        bid = self.enter()
        r = self.allocate(bid["id"], self.v1)
        self.assertEqual(r.status_code, 200, r.text)
        out = r.json()
        today = svc.today_ist()
        self.assertEqual(out["status"], "Allocated")
        self.assertEqual(out["vendor_name"], "Frost Point")
        self.assertEqual(out["confirm_by"], (today + timedelta(days=1)).isoformat())
        self.assertEqual(out["submit_by"], (today + timedelta(days=9)).isoformat())
        self.assertIn(("frost@t.com", "Bid allocated to you: GEM/2026/B/5821904"), self.sent)

    def test_second_vendor_is_refused_while_locked(self):
        bid = self.enter()
        self.allocate(bid["id"], self.v1)
        r = self.allocate(bid["id"], self.v2, who=self.sales)
        self.assertEqual(r.status_code, 409)
        self.assertIn("Already allocated", r.json()["detail"])
        self.assertEqual(self.bid(bid["id"]).vendor_id, self.v1.id)

    def test_ticked_user_cannot_override_but_admin_and_sub_admin_can(self):
        bid = self.enter()
        self.allocate(bid["id"], self.v1)
        r = self.allocate(bid["id"], self.v2, who=self.sales, reason="because")
        self.assertEqual(r.status_code, 409)
        r = self.allocate(bid["id"], self.v2, who=self.admin)
        self.assertEqual(r.status_code, 400)  # reason required
        r = self.allocate(bid["id"], self.v2, who=self.admin, reason="Customer asked for Arctic")
        self.assertEqual(r.status_code, 200, r.text)
        self.assertEqual(r.json()["vendor_name"], "Arctic Sales")
        self.assertTrue(any(e["action"] == "override" and "Customer asked" in e["text"] for e in r.json()["events"]))
        self.assertIn(("frost@t.com", "Bid taken back by INDcool: GEM/2026/B/5821904"), self.sent)
        r = self.allocate(bid["id"], self.v3, who=self.sub, reason="Sub admin override")
        self.assertEqual(r.status_code, 200)
        self.assertEqual(r.json()["vendor_name"], "Cool Zone")

    def test_self_bid_is_confirmed_at_once_and_sends_no_vendor_mail(self):
        bid = self.enter()
        r = self.client.post(f"/api/bids/{bid['id']}/allocate", json={"self_bid": True}, headers=self.h(self.sub))
        self.assertEqual(r.status_code, 200, r.text)
        self.assertEqual((r.json()["status"], r.json()["vendor_name"]), ("Confirmed", "INDcool (Self)"))
        self.assertEqual(self.sent, [])

    def test_allocation_list_has_one_entry_per_vendor_login(self):
        # a second record for the same firm and login, a firm with no login, an inactive record, and a same-name firm with another login
        self.db.add_all([
            Vendor(vendor_code="V001-DUP", name_of_firm="FROST POINT", email="frost@t.com", is_active=True),
            Vendor(vendor_code="V900", name_of_firm="Nobody Has A Login", email="nologin@t.com", is_active=True),
        ])
        old = Vendor(vendor_code="V901", name_of_firm="Switched Off Traders", email="off@t.com", is_active=False)
        self.db.add(old)
        self.db.flush()
        self._user("off@t.com", "vendor", "Switched Off Traders")
        self.db.add(Vendor(vendor_code="V902", name_of_firm="Arctic Sales", email="arctic2@t.com", is_active=True))
        self._user("arctic2@t.com", "vendor", "Arctic Sales Two")
        self.db.commit()
        rows = self.client.get("/api/bids/vendors", headers=self.h(self.sub)).json()
        names = [r["name"] for r in rows]
        self.assertEqual(len([r for r in rows if r["email"] == "frost@t.com"]), 1)
        newest = self.db.scalars(select(Vendor).where(Vendor.email == "frost@t.com").order_by(Vendor.id.desc())).first()
        self.assertEqual([r["id"] for r in rows if r["email"] == "frost@t.com"], [newest.id])
        self.assertFalse(any("Nobody" in n for n in names))
        self.assertFalse(any("Switched Off" in n for n in names))
        arctics = [n for n in names if n.startswith("Arctic Sales")]
        self.assertEqual(len(arctics), 2)
        self.assertEqual(len(set(arctics)), 2, "same firm name with two logins must be told apart")
        firms = [n.split(" (")[0].lower() for n in names]
        self.assertEqual(firms, sorted(firms))
        # a bid given from this list is the bid the vendor sees after logging in
        pick = next(r for r in rows if r["email"] == "frost@t.com")
        bid = self.enter()
        self.client.post(f"/api/bids/{bid['id']}/allocate", json={"vendor_id": pick["id"]}, headers=self.h(self.sub))
        mine = self.client.get("/api/bids", headers=self.h(self.vu1)).json()
        self.assertEqual([b["bid_number"] for b in mine], [bid["bid_number"]])

    def test_a_bid_can_have_several_items(self):
        bid = self.enter(number="GEM/2026/B/7960553", title="Split AC in three sizes", lines=[
            {"item": "Split AC 1.3 Ton - 1.7 Ton", "quantity": 10}, {"item": "1.8-2.2 Ton", "quantity": 8}, {"item": "0.8-1.2 Ton", "quantity": None}])
        self.assertEqual([(l["item"], l["quantity"]) for l in bid["lines"]], [("Split AC 1.3 Ton - 1.7 Ton", 10), ("1.8-2.2 Ton", 8), ("0.8-1.2 Ton", None)])
        self.assertEqual(bid["quantity"], 18, "the bid quantity is the total of the lines")
        listed = self.client.get("/api/bids", headers=self.h(self.sub)).json()
        self.assertEqual(len(listed[0]["lines"]), 3)
        self.assertEqual(len(self.client.get("/api/bids", params={"q": "1.8 2.2 ton"}, headers=self.h(self.sub)).json()), 1)
        self.assertEqual(len(self.client.get("/api/bids", params={"q": "7960553"}, headers=self.h(self.sub)).json()), 1)

    def test_item_lines_can_be_changed_and_cleared(self):
        bid = self.enter(lines=[{"item": "Window AC", "quantity": 4}])
        two = [{"item": "Window AC", "quantity": 4}, {"item": "Cassette AC", "quantity": 6}]
        r = self.client.put(f"/api/bids/{bid['id']}", json={"lines": two}, headers=self.h(self.sub))
        self.assertEqual(r.status_code, 200, r.text)
        self.assertEqual((len(r.json()["lines"]), r.json()["quantity"]), (2, 10))
        self.assertTrue(any(e["action"] == "edited" and "items" in e["text"] for e in r.json()["events"]))
        same = self.client.put(f"/api/bids/{bid['id']}", json={"lines": two}, headers=self.h(self.sub))
        self.assertEqual(len([e for e in same.json()["events"] if e["action"] == "edited"]), 1, "saving the same lines again logs nothing")
        untouched = self.client.put(f"/api/bids/{bid['id']}", json={"title": "Window AC, new title"}, headers=self.h(self.sub))
        self.assertEqual(len(untouched.json()["lines"]), 2)
        cleared = self.client.put(f"/api/bids/{bid['id']}", json={"lines": []}, headers=self.h(self.sub))
        self.assertEqual(cleared.json()["lines"], [])

    def test_item_lines_are_checked(self):
        today = svc.today_ist()
        base = {"bid_number": "GEM/2026/B/1", "title": "Split AC", "end_date": (today + timedelta(days=5)).isoformat()}
        twice = self.client.post("/api/bids", json={**base, "lines": [{"item": "1.5 Ton", "quantity": 2}, {"item": " 1.5  ton ", "quantity": 3}]}, headers=self.h(self.sub))
        self.assertEqual(twice.status_code, 400)
        self.assertIn("listed twice", twice.json()["detail"])
        self.assertEqual(self.client.post("/api/bids", json={**base, "lines": [{"item": "   ", "quantity": 2}]}, headers=self.h(self.sub)).status_code, 422)
        self.assertEqual(self.client.post("/api/bids", json={**base, "lines": [{"item": "1.5 Ton", "quantity": -1}]}, headers=self.h(self.sub)).status_code, 422)
        self.assertEqual(self.client.get("/api/bids", headers=self.h(self.sub)).json(), [], "a refused bid is not kept")

    def test_vendor_sees_the_items_of_their_bid(self):
        bid = self.enter(lines=[{"item": "Split AC 1.5 Ton", "quantity": 4}])
        self.allocate(bid["id"], self.v1)
        mine = self.client.get(f"/api/bids/{bid['id']}", headers=self.h(self.vu1)).json()
        self.assertEqual([l["item"] for l in mine["lines"]], ["Split AC 1.5 Ton"])

    def test_vendor_cannot_allocate(self):
        bid = self.enter()
        r = self.client.post(f"/api/bids/{bid['id']}/allocate", json={"vendor_id": self.v1.id}, headers=self.h(self.vu1))
        self.assertEqual(r.status_code, 403)

    # --- vendor flow
    def test_vendor_sees_only_own_bids_and_hides_internals(self):
        a = self.enter(notes="internal note")
        b = self.enter(number="GEM/2026/B/5790112", title="Water cooler")
        self.allocate(a["id"], self.v1)
        self.allocate(b["id"], self.v2)
        mine = self.client.get("/api/bids", headers=self.h(self.vu1)).json()
        self.assertEqual([x["bid_number"] for x in mine], ["GEM/2026/B/5821904"])
        self.assertIsNone(mine[0]["notes"])
        self.assertEqual(self.client.get(f"/api/bids/{b['id']}", headers=self.h(self.vu1)).status_code, 404)
        detail = self.client.get(f"/api/bids/{a['id']}", headers=self.h(self.vu1)).json()
        self.assertTrue(all("Arctic" not in e["text"] for e in detail["events"]))
        self.assertNotIn("entered", [e["action"] for e in detail["events"]])

    def test_vendor_confirm_submit_then_result(self):
        bid = self.enter()
        self.allocate(bid["id"], self.v1)
        r = self.client.post(f"/api/bids/{bid['id']}/confirm", headers=self.h(self.vu1))
        self.assertEqual((r.status_code, r.json()["status"]), (200, "Confirmed"))
        r = self.client.post(f"/api/bids/{bid['id']}/submit", json={"reference": "GEM-ACK-1"}, headers=self.h(self.vu1))
        self.assertEqual((r.status_code, r.json()["status"]), (200, "Submitted"))
        r = self.client.post(f"/api/bids/{bid['id']}/result", json={"result": "Won"}, headers=self.h(self.vu1))
        self.assertEqual(r.status_code, 403)
        r = self.client.post(f"/api/bids/{bid['id']}/result", json={"result": "Won", "note": "L1"}, headers=self.h(self.sales))
        self.assertEqual((r.status_code, r.json()["status"]), (200, "Won"))

    def test_other_vendor_cannot_confirm(self):
        bid = self.enter()
        self.allocate(bid["id"], self.v1)
        r = self.client.post(f"/api/bids/{bid['id']}/confirm", headers=self.h(self.vu2))
        self.assertEqual(r.status_code, 404)

    def test_vendor_decline_frees_the_bid(self):
        bid = self.enter()
        self.allocate(bid["id"], self.v1)
        r = self.client.post(f"/api/bids/{bid['id']}/decline", json={"reason": "No stock"}, headers=self.h(self.vu1))
        self.assertEqual(r.status_code, 200, r.text)
        b = self.bid(bid["id"])
        self.assertEqual((b.status, b.vendor_id), ("Open", None))

    # --- time rules
    def test_release_when_not_confirmed(self):
        bid = self.enter()
        self.allocate(bid["id"], self.v1)
        today = svc.today_ist()
        self.db.expire_all()
        out = svc.run_rules(self.db, today + timedelta(days=1), send_reminders=False)
        self.assertEqual(out["released"], 0)  # the confirm-by day itself is still fine
        out = svc.run_rules(self.db, today + timedelta(days=2), send_reminders=False)
        self.assertEqual(out["released"], 1)
        b = self.bid(bid["id"])
        self.assertEqual((b.status, b.vendor_id), ("Open", None))
        self.assertIn(("frost@t.com", "Bid released from you: GEM/2026/B/5821904"), self.sent)
        self.assertTrue(any(e.action == "auto_released" and e.actor_name == "System" for e in self.db.scalars(select(BidEvent))))
        # free again, so another vendor can take it
        self.assertEqual(self.allocate(bid["id"], self.v2).status_code, 200)

    def test_release_when_not_submitted_by_submit_date(self):
        bid = self.enter()
        self.allocate(bid["id"], self.v1)
        self.client.post(f"/api/bids/{bid['id']}/confirm", headers=self.h(self.vu1))
        today = svc.today_ist()
        b = self.bid(bid["id"])
        out = svc.run_rules(self.db, b.submit_by, send_reminders=False)
        self.assertEqual(out["released"], 0)
        out = svc.run_rules(self.db, b.submit_by + timedelta(days=1), send_reminders=False)
        self.assertEqual(out["released"], 1)
        self.assertEqual(self.bid(bid["id"]).status, "Open")
        del today

    def test_submitted_bid_is_never_auto_released_and_self_bid_neither(self):
        a = self.enter()
        self.allocate(a["id"], self.v1)
        self.client.post(f"/api/bids/{a['id']}/confirm", headers=self.h(self.vu1))
        self.client.post(f"/api/bids/{a['id']}/submit", headers=self.h(self.vu1))
        s = self.enter(number="GEM/2026/B/2")
        self.client.post(f"/api/bids/{s['id']}/allocate", json={"self_bid": True}, headers=self.h(self.sub))
        end = svc.today_ist() + timedelta(days=10)
        svc.run_rules(self.db, end - timedelta(days=1), send_reminders=False)
        self.assertEqual(self.bid(a["id"]).status, "Submitted")
        self.assertEqual(self.bid(s["id"]).status, "Confirmed")

    def test_past_end_date_closes_unsubmitted_bids(self):
        free = self.enter(number="GEM/2026/B/10")
        held = self.enter(number="GEM/2026/B/11")
        self.allocate(held["id"], self.v1)
        end = svc.today_ist() + timedelta(days=10)
        out = svc.run_rules(self.db, end + timedelta(days=1), send_reminders=False)
        self.assertEqual(self.bid(free["id"]).status, "Closed")
        self.assertIn(self.bid(held["id"]).status, ("Closed", "Open"))
        self.assertGreaterEqual(out["closed"], 1)
        r = self.allocate(free["id"], self.v1, who=self.admin, reason="late")
        self.assertEqual(r.status_code, 409)

    # --- reminders
    def test_reminders_daily_from_three_days_to_closing_vendor_only_once_a_day(self):
        bid = self.enter(days=6)
        self.allocate(bid["id"], self.v1)
        self.client.post(f"/api/bids/{bid['id']}/confirm", headers=self.h(self.vu1))
        end = svc.today_ist() + timedelta(days=6)
        for offset, expected in ((5, 0), (4, 0), (3, 1), (2, 1), (1, 1), (0, 0)):  # on closing day an unsubmitted bid has already gone back to INDcool
            self.sent.clear()
            day = end - timedelta(days=offset)
            out = svc.run_rules(self.db, day, send_reminders=True)
            self.assertEqual(out["reminders"], expected, f"{offset} days before")
            reminder_mails = [m for m in self.sent if m[1].startswith("Reminder:")]
            self.assertEqual(len(reminder_mails), expected)
            if expected:
                self.assertEqual(reminder_mails[0][0], "frost@t.com")
                self.assertIn(bid["bid_number"], reminder_mails[0][1])
            self.sent.clear()
            self.assertEqual(svc.run_rules(self.db, day, send_reminders=True)["reminders"], 0)  # no double send same day
        self.assertEqual(len(self.db.scalars(select(BidReminder)).all()), 3)
        self.assertEqual(self.bid(bid["id"]).status, "Open")

    def test_no_reminder_after_submission_or_for_self_bids(self):
        bid = self.enter(days=3)
        self.allocate(bid["id"], self.v1)
        self.client.post(f"/api/bids/{bid['id']}/confirm", headers=self.h(self.vu1))
        self.client.post(f"/api/bids/{bid['id']}/submit", headers=self.h(self.vu1))
        s = self.enter(number="GEM/2026/B/2", days=3)
        self.client.post(f"/api/bids/{s['id']}/allocate", json={"self_bid": True}, headers=self.h(self.sub))
        self.sent.clear()
        self.assertEqual(svc.run_rules(self.db, svc.today_ist(), send_reminders=True)["reminders"], 0)
        self.assertEqual([m for m in self.sent if m[1].startswith("Reminder")], [])

    # --- vendor requests
    def test_request_a_free_bid_reaches_the_team_and_can_be_allocated(self):
        bid = self.enter(number="GEM/2026/B/5855021", title="Hard top deep freezer")
        r = self.client.post("/api/bids/requests", json={"bid_number": "gem 2026 b 5855021", "note": "stock ready"}, headers=self.h(self.vu1))
        self.assertEqual(r.status_code, 201, r.text)
        self.assertEqual(r.json()["bid_id"], bid["id"])
        self.client.post("/api/bids/requests", json={"bid_number": "GEM/2026/B/5855021"}, headers=self.h(self.vu2))
        rows = self.client.get("/api/bids/requests?state=Requested", headers=self.h(self.sub)).json()
        self.assertEqual(len(rows), 2)
        self.assertTrue(all(x["asked_by_others"] == 1 for x in rows))
        first = rows[-1]
        r = self.client.post(f"/api/bids/requests/{first['id']}/allocate", headers=self.h(self.sub))
        self.assertEqual(r.status_code, 200, r.text)
        self.assertEqual(self.bid(bid["id"]).vendor_id, first["vendor_id"])
        left = self.client.get("/api/bids/requests", headers=self.h(self.vu2 if first["vendor_id"] == self.v1.id else self.vu1)).json()
        self.assertEqual(left[0]["status"], "Not available")
        self.assertEqual(left[0]["decision_note"], "Not available, already allocated")

    def test_request_for_a_locked_bid_says_already_allocated_without_naming_holder(self):
        bid = self.enter()
        self.allocate(bid["id"], self.v1)
        r = self.client.post("/api/bids/requests", json={"bid_number": bid["bid_number"]}, headers=self.h(self.vu2))
        self.assertEqual(r.status_code, 409)
        self.assertEqual(r.json()["detail"], "Already allocated")
        hits = self.client.get("/api/bids/lookup?q=5821", headers=self.h(self.vu2)).json()
        self.assertEqual(hits[0]["availability"], "allocated")
        self.assertNotIn("Frost", str(hits))
        mine = self.client.get("/api/bids/lookup?q=5821", headers=self.h(self.vu1)).json()
        self.assertEqual(mine[0]["availability"], "mine")

    def test_unknown_number_becomes_an_unlinked_request_then_links_when_entered(self):
        r = self.client.post("/api/bids/requests", json={"bid_number": "GEM/2026/B/9999999", "note": "new one"}, headers=self.h(self.vu1))
        self.assertEqual(r.status_code, 201)
        self.assertIsNone(r.json()["bid_id"])
        self.assertTrue(any("not entered" in s[1].lower() or "Bid request" in s[1] for s in self.sent))
        row = self.client.get("/api/bids/requests", headers=self.h(self.sub)).json()[0]
        self.assertEqual(self.client.post(f"/api/bids/requests/{row['id']}/allocate", headers=self.h(self.sub)).status_code, 409)
        bid = self.enter(number="GEM/2026/B/9999999", title="Ceiling fan")
        row = self.client.get("/api/bids/requests", headers=self.h(self.sub)).json()[0]
        self.assertEqual(row["bid_id"], bid["id"])
        self.assertEqual(self.client.post(f"/api/bids/requests/{row['id']}/allocate", headers=self.h(self.sub)).status_code, 200)

    def test_double_request_refused_and_decline_tells_vendor(self):
        self.enter(number="GEM/2026/B/77")
        self.assertEqual(self.client.post("/api/bids/requests", json={"bid_number": "GEM/2026/B/77"}, headers=self.h(self.vu1)).status_code, 201)
        self.assertEqual(self.client.post("/api/bids/requests", json={"bid_number": "gem 2026 b 77"}, headers=self.h(self.vu1)).status_code, 409)
        rid = self.client.get("/api/bids/requests", headers=self.h(self.sub)).json()[0]["id"]
        self.sent.clear()
        r = self.client.post(f"/api/bids/requests/{rid}/decline", json={"note": "Not this time"}, headers=self.h(self.sub))
        self.assertEqual(r.status_code, 200)
        self.assertEqual(r.json()["status"], "Declined")
        self.assertTrue(any(m[0] == "frost@t.com" and "declined" in m[1] for m in self.sent))

    def test_vendors_see_only_their_own_requests(self):
        self.enter(number="GEM/2026/B/77")
        self.client.post("/api/bids/requests", json={"bid_number": "GEM/2026/B/77"}, headers=self.h(self.vu1))
        self.assertEqual(len(self.client.get("/api/bids/requests", headers=self.h(self.vu2)).json()), 0)
        self.assertEqual(len(self.client.get("/api/bids/requests", headers=self.h(self.vu1)).json()), 1)
        self.assertEqual(self.client.post("/api/bids/requests", json={"bid_number": "x"}, headers=self.h(self.sub)).status_code, 403)

    # --- list search and filters
    def test_list_search_filters_and_ranking(self):
        self.enter(number="GEM/2026/B/5821904", title="Split AC 120 units")
        self.enter(number="GEM/2026/B/5855021", title="Hard top deep freezer")
        self.enter(number="UPPWD/2026-27/T-0441", title="Window AC", bid_type="State govt")
        names = lambda q="", **kw: [b["bid_number"] for b in self.client.get("/api/bids", params={"q": q, **kw}, headers=self.h(self.sub)).json()]
        self.assertEqual(names("5821 904"), ["GEM/2026/B/5821904"])
        self.assertEqual(names("582l904"), ["GEM/2026/B/5821904"])
        self.assertEqual(len(names("")), 3)
        self.assertEqual(names(bid_type="State govt"), ["UPPWD/2026-27/T-0441"])
        self.assertEqual(names(category="Deep Freezer"), ["GEM/2026/B/5855021"])
        self.assertEqual(names("uppwd 0441"), ["UPPWD/2026-27/T-0441"])

    def test_edit_bid_and_duplicate_number_guard(self):
        a = self.enter()
        b = self.enter(number="GEM/2026/B/2")
        r = self.client.put(f"/api/bids/{a['id']}", json={"title": "Window AC 40 units", "emd_amount": 5000}, headers=self.h(self.sales))
        self.assertEqual(r.status_code, 200, r.text)
        self.assertEqual(r.json()["title"], "Window AC 40 units")
        r = self.client.put(f"/api/bids/{a['id']}", json={"bid_number": b["bid_number"]}, headers=self.h(self.sales))
        self.assertEqual(r.status_code, 409)
        r = self.client.put(f"/api/bids/{a['id']}", json={"title": "x"}, headers=self.h(self.vu1))
        self.assertEqual(r.status_code, 403)

    def test_end_before_publish_is_refused(self):
        r = self.client.post("/api/bids", json={"bid_number": "GEM/3", "title": "ab", "publish_date": "2026-10-10", "end_date": "2026-10-01"}, headers=self.h(self.sub))
        self.assertEqual(r.status_code, 400)

    def test_manual_run_rules_is_admin_side_only(self):
        self.assertEqual(self.client.post("/api/bids/run-rules", headers=self.h(self.sales)).status_code, 403)
        self.assertEqual(self.client.post("/api/bids/run-rules", headers=self.h(self.vu1)).status_code, 403)
        self.assertEqual(self.client.post("/api/bids/run-rules", headers=self.h(self.admin)).status_code, 200)


if __name__ == "__main__":
    unittest.main()
