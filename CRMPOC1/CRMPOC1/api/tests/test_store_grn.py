from __future__ import annotations

import os
import sys
import unittest
from datetime import date
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
os.environ.setdefault("MYSQL_DATABASE_URL", "sqlite://")
os.environ.setdefault("SITE_API_KEY", "k")
os.environ.setdefault("SARVAM_API_KEY", "k")
os.environ.setdefault("BOUNCE_CHECK_ENABLED", "false")

from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

import app.models  # noqa: F401  (registers every table)
from app.config import settings
from app.database import Base, get_db
from app.deps import get_current_user
from app.main import app as fastapi_app
from app.models.item_master import ItemMaster
from app.models.order import Order, OrderItem
from app.models.user import User
from app.seed import seed_roles


class StoreGrnTests(unittest.TestCase):
    def setUp(self):
        self.engine = create_engine("sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool)
        Base.metadata.create_all(self.engine)
        self.Session = sessionmaker(bind=self.engine, expire_on_commit=False, future=True)
        db = self.Session()
        seed_roles(db)
        db.commit()
        self.users = {}
        for name, role in [("keeper", "store_keeper"), ("manager", "store_manager"), ("boss", "admin"), ("caller", "callcenter"), ("keeper2", "store_keeper")]:
            u = User(name=name.title(), email=f"{name}@test.com", password_hash="x", role=role, is_active=True)
            db.add(u)
            self.users[name] = u
        self.ac = ItemMaster(item_code="AC15", item_name="Split AC 1.5T 5 star", serial_count=2, is_active=True)
        self.cmp = ItemMaster(item_code="CMP15", item_name="Compressor 1.5T", serial_count=1, is_active=True)
        self.fan = ItemMaster(item_code="FAN01", item_name="Fan motor", serial_count=0, is_active=True)
        db.add_all([self.ac, self.cmp, self.fan])
        db.commit()
        self.db = db
        self.current = "keeper"

        def _db():
            s = self.Session()
            try:
                yield s
            finally:
                s.close()

        fastapi_app.dependency_overrides[get_db] = _db
        fastapi_app.dependency_overrides[get_current_user] = lambda: self.users[self.current]
        self.c = TestClient(fastapi_app)

    def tearDown(self):
        fastapi_app.dependency_overrides.clear()
        self.db.close()
        self.engine.dispose()

    def as_(self, who):
        self.current = who

    def body(self, lines=None, ref="COM/143"):
        return {
            "source_type": "Purchase",
            "supplier_name": "OEM Ltd",
            "reference_no": ref,
            "lines": lines
            if lines is not None
            else [
                {"item_id": self.ac.id, "stock_type": "Fresh", "serial_no": "idu-88412", "serial_no_2": "odu-88412", "unit_cost": 30000},
                {"item_id": self.fan.id, "stock_type": "Spare", "qty": 5, "unit_cost": 800},
            ],
        }

    def make_posted(self, **kw):
        self.as_("keeper")
        g = self.c.post("/api/store/grns", json=self.body(**kw)).json()
        self.assertEqual(self.c.post(f"/api/store/grns/{g['id']}/submit").status_code, 200)
        self.as_("manager")
        r = self.c.post(f"/api/store/grns/{g['id']}/approve")
        self.assertEqual(r.status_code, 200, r.text)
        return r.json()

    def test_full_lifecycle_adds_stock_and_ledger(self):
        self.as_("keeper")
        r = self.c.post("/api/store/grns", json=self.body())
        self.assertEqual(r.status_code, 201, r.text)
        g = r.json()
        self.assertEqual(g["status"], "Draft")
        self.assertTrue(g["grn_no"].startswith("GRN-"))
        self.assertEqual(g["total_units"], 6)
        self.assertEqual(self.c.get("/api/store/stock").status_code, 200)
        self.assertEqual(self.c.get("/api/store/stock").json(), [])  # nothing is stock until posted

        self.assertEqual(self.c.post(f"/api/store/grns/{g['id']}/submit").json()["status"], "Pending Approval")
        self.assertEqual(self.c.post(f"/api/store/grns/{g['id']}/approve").status_code, 403)  # keeper cannot approve

        self.as_("manager")
        posted = self.c.post(f"/api/store/grns/{g['id']}/approve").json()
        self.assertEqual(posted["status"], "Posted")
        self.assertEqual(posted["approved_by_name"], "Manager")

        stock = {row["item_code"]: row for row in self.c.get("/api/store/stock").json()}
        self.assertEqual(stock["AC15"]["available"], 1)
        self.assertEqual(stock["FAN01"]["available"], 5)
        units = self.c.get("/api/store/stock/units?search=IDU-88412").json()["items"]
        self.assertEqual(units[0]["serial_no"], "IDU-88412")  # stored in capitals
        self.assertEqual(units[0]["serial_no_2"], "ODU-88412")
        ledger = self.c.get("/api/store/ledger").json()["items"]
        self.assertEqual(sorted((x["item_code"], x["qty_in"]) for x in ledger), [("AC15", 1), ("FAN01", 5)])
        self.assertTrue(all(x["by_user_name"] == "Manager" for x in ledger))

    def test_submit_needs_a_reference_number(self):
        self.as_("keeper")
        g = self.c.post("/api/store/grns", json=self.body(ref="")).json()
        r = self.c.post(f"/api/store/grns/{g['id']}/submit")
        self.assertEqual(r.status_code, 400)
        self.assertIn("bill, challan or LR", r.json()["detail"])

    def test_duplicate_serials_are_blocked_everywhere(self):
        self.make_posted()
        self.as_("keeper")
        # already in the store
        r = self.c.post("/api/store/grns", json=self.body(lines=[{"item_id": self.ac.id, "serial_no": "IDU-88412", "serial_no_2": "ODU-99999"}]))
        self.assertEqual(r.status_code, 409)
        self.assertIn("already in the store", r.json()["detail"])
        # twice on the same GRN
        r = self.c.post("/api/store/grns", json=self.body(lines=[
            {"item_id": self.cmp.id, "serial_no": "CMP-20101"}, {"item_id": self.cmp.id, "serial_no": "cmp-20101"}]))
        self.assertEqual(r.status_code, 400)
        self.assertIn("twice", r.json()["detail"])
        # on another open GRN
        self.assertEqual(self.c.post("/api/store/grns", json=self.body(lines=[{"item_id": self.cmp.id, "serial_no": "CMP-30001"}])).status_code, 201)
        r = self.c.post("/api/store/grns", json=self.body(lines=[{"item_id": self.cmp.id, "serial_no": "CMP-30001"}]))
        self.assertEqual(r.status_code, 409)
        # already on an order
        order = Order(order_no="GEMC-1", order_date=date(2026, 10, 1), status="Pending")
        self.db.add(order)
        self.db.flush()
        self.db.add(OrderItem(order_id=order.id, item_code="CMP15", serial_no="CMP-40001"))
        self.db.commit()
        chk = self.c.post("/api/store/serials/check", json={"serial": "cmp-40001"}).json()
        self.assertFalse(chk["ok"])
        self.assertIn("GEMC-1", chk["reason"])
        self.assertTrue(self.c.post("/api/store/serials/check", json={"serial": "CMP-50001"}).json()["ok"])
        self.assertFalse(self.c.post("/api/store/serials/check", json={"serial": "12"}).json()["ok"])

    def test_line_rules_follow_the_item_master(self):
        self.as_("keeper")
        cases = [
            ([{"item_id": self.fan.id, "serial_no": "FAN-00001"}], "counted by quantity"),
            ([{"item_id": self.cmp.id, "serial_no": "12", "qty": 1}], "valid serial"),
            ([{"item_id": self.cmp.id, "serial_no": "CMP-10001", "qty": 2}], "one at a time"),
            ([{"item_id": self.ac.id, "serial_no": "IDU-88412"}], "serial number 2 is required"),
            ([{"item_id": self.cmp.id}], "serial number 1 is required"),
            ([{"item_id": 99999, "serial_no": "CMP-10001"}], "not found"),
        ]
        for lines, text in cases:
            r = self.c.post("/api/store/grns", json=self.body(lines=lines))
            self.assertEqual(r.status_code, 400, (lines, r.text))
            self.assertIn(text, r.json()["detail"])

    def test_damaged_goes_to_quarantine_not_available(self):
        self.make_posted(lines=[{"item_id": self.cmp.id, "serial_no": "CMP-10031", "condition": "Damaged"}, {"item_id": self.cmp.id, "serial_no": "CMP-10032"}])
        row = self.c.get("/api/store/stock").json()[0]
        self.assertEqual((row["available"], row["quarantine"], row["total"]), (1, 1, 2))

    def test_maker_checker_blocks_approving_your_own_grn(self):
        self.as_("manager")
        g = self.c.post("/api/store/grns", json=self.body()).json()
        self.c.post(f"/api/store/grns/{g['id']}/submit")
        r = self.c.post(f"/api/store/grns/{g['id']}/approve")
        self.assertEqual(r.status_code, 403)
        self.assertFalse(self.c.get(f"/api/store/grns/{g['id']}").json()["can_approve"])
        with patch.object(settings, "store_maker_checker", False):
            self.assertEqual(self.c.post(f"/api/store/grns/{g['id']}/approve").status_code, 200)

    def test_reject_sends_back_to_draft_and_it_can_be_fixed(self):
        self.as_("keeper")
        g = self.c.post("/api/store/grns", json=self.body()).json()
        self.c.post(f"/api/store/grns/{g['id']}/submit")
        self.as_("manager")
        r = self.c.post(f"/api/store/grns/{g['id']}/reject", json={"reason": "Bill number is wrong"})
        self.assertEqual(r.status_code, 200)
        self.assertEqual(r.json()["status"], "Draft")
        self.assertIn("Bill number is wrong", r.json()["reject_reason"])
        self.as_("keeper")
        fixed = self.body(ref="COM/144")
        self.assertEqual(self.c.put(f"/api/store/grns/{g['id']}", json=fixed).json()["reference_no"], "COM/144")
        self.assertEqual(self.c.post(f"/api/store/grns/{g['id']}/submit").json()["status"], "Pending Approval")
        self.assertEqual(self.c.put(f"/api/store/grns/{g['id']}", json=fixed).status_code, 409)  # submitted, so no longer a draft
        self.as_("keeper2")
        self.assertEqual(self.c.put(f"/api/store/grns/{g['id']}", json=fixed).status_code, 403)  # and not their GRN

    def test_only_the_creator_edits_a_draft(self):
        self.as_("keeper")
        g = self.c.post("/api/store/grns", json=self.body()).json()
        self.as_("keeper2")
        self.assertEqual(self.c.put(f"/api/store/grns/{g['id']}", json=self.body()).status_code, 403)
        self.assertEqual(self.c.delete(f"/api/store/grns/{g['id']}").status_code, 403)
        self.as_("keeper")
        self.assertEqual(self.c.delete(f"/api/store/grns/{g['id']}").status_code, 204)

    def test_grn_numbers_continue_after_a_deleted_draft(self):
        self.as_("keeper")
        a = self.c.post("/api/store/grns", json=self.body(lines=[])).json()
        b = self.c.post("/api/store/grns", json=self.body(lines=[])).json()
        self.c.delete(f"/api/store/grns/{a['id']}")
        c = self.c.post("/api/store/grns", json=self.body(lines=[])).json()
        self.assertEqual((a["grn_no"], b["grn_no"], c["grn_no"]), ("GRN-0001", "GRN-0002", "GRN-0003"))

    def test_roles_and_permissions(self):
        self.as_("caller")
        self.assertEqual(self.c.get("/api/store/grns").status_code, 403)
        self.assertEqual(self.c.get("/api/store/stock").status_code, 403)
        self.assertEqual(self.c.post("/api/store/grns", json=self.body()).status_code, 403)
        self.assertEqual(self.c.get("/api/store/lookup/items").status_code, 403)
        self.as_("keeper")
        self.assertEqual(self.c.get("/api/store/stock").status_code, 200)
        self.assertEqual(self.c.get("/api/store/meta").json()["can_approve"], False)
        self.assertEqual(len(self.c.get("/api/store/lookup/items").json()), 3)
        self.as_("manager")
        self.assertEqual(self.c.get("/api/store/meta").json()["can_approve"], True)
        # admin does everything, including approving someone else's GRN
        self.as_("keeper")
        g = self.c.post("/api/store/grns", json=self.body()).json()
        self.c.post(f"/api/store/grns/{g['id']}/submit")
        self.as_("boss")
        self.assertEqual(self.c.post(f"/api/store/grns/{g['id']}/approve").json()["status"], "Posted")


if __name__ == "__main__":
    unittest.main()
