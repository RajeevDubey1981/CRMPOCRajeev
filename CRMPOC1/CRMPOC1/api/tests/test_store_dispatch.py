from __future__ import annotations

import io
import json
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
from sqlalchemy import create_engine, select
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

import app.models  # noqa: F401  (registers every table)
from app.database import Base, get_db
from app.deps import get_current_user
from app.main import app as fastapi_app
from app.models.courier import Courier
from app.models.item_master import ItemMaster
from app.models.order import Order, OrderItem
from app.models.store import StoreLedger, StoreStock
from app.models.user import User
from app.seed import seed_roles


class StoreDispatchTests(unittest.TestCase):
    def setUp(self):
        self.engine = create_engine("sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool)
        Base.metadata.create_all(self.engine)
        self.Session = sessionmaker(bind=self.engine, expire_on_commit=False, future=True)
        db = self.Session()
        seed_roles(db)
        db.commit()
        self.users = {}
        for name, role in [("keeper", "store_keeper"), ("manager", "store_manager"), ("boss", "admin"), ("caller", "callcenter")]:
            u = User(name=name.title(), email=f"{name}@test.com", password_hash="x", role=role, is_active=True)
            db.add(u)
            self.users[name] = u
        self.ac = ItemMaster(item_code="AC15", item_name="Split AC 1.5T 5 star", serial_count=2, is_active=True)
        self.fan = ItemMaster(item_code="FAN01", item_name="Fan motor", serial_count=0, is_active=True)
        self.courier = Courier(courier_name="BlueDart")
        db.add_all([self.ac, self.fan, self.courier])
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

    # helpers ---------------------------------------------------------------
    def receive(self, lines, ref):
        self.as_("keeper")
        g = self.c.post("/api/store/grns", json={"source_type": "Purchase", "supplier_name": "Own assembly", "reference_no": ref, "lines": lines})
        self.assertEqual(g.status_code, 201, g.text)
        gid = g.json()["id"]
        self.assertEqual(self.c.post(f"/api/store/grns/{gid}/submit").status_code, 200)
        self.as_("manager")
        r = self.c.post(f"/api/store/grns/{gid}/approve")
        self.assertEqual(r.status_code, 200, r.text)

    def ac_line(self, n):
        return {"item_id": self.ac.id, "stock_type": "Fresh", "serial_no": f"IDU-{n}", "serial_no_2": f"ODU-{n}"}

    def make_order(self, lines, *, fulfilment="Store", bill=None, order_no=None):
        db = self.Session()
        o = Order(order_no=order_no or f"ORD-{db.query(Order).count() + 1}", order_date=date.today(), status="Pending",
                  fulfilment=fulfilment, oem_bill_no=bill, customer_name="Frost Point", customer_city="Noida")
        db.add(o)
        db.flush()
        for item in lines:
            db.add(OrderItem(order_id=o.id, item_id=item.id, item_code=item.item_code, item_qty=1))
        db.commit()
        oid = o.id
        db.close()
        return oid

    def set_bill(self, oid, bill="INV/26-27/0412"):
        db = self.Session()
        db.get(Order, oid).oem_bill_no = bill
        db.commit()
        db.close()

    def unit_status(self, serial):
        db = self.Session()
        try:
            return db.scalar(select(StoreStock.status).where(StoreStock.serial_no == serial))
        finally:
            db.close()

    # tests -----------------------------------------------------------------
    def test_reserve_takes_oldest_first_and_reports_shortage(self):
        self.receive([self.ac_line("100"), self.ac_line("101")], "B1")
        self.receive([self.ac_line("200")], "B2")
        oid = self.make_order([self.ac] * 4)
        self.as_("keeper")
        r = self.c.post(f"/api/store/orders/{oid}/reserve")
        self.assertEqual(r.status_code, 200, r.text)
        out = r.json()
        self.assertEqual(out["reserved"], 3)
        self.assertEqual(out["short"][0]["missing"], 1)
        held = [ln["serial_no"] for ln in out["order"]["lines"] if ln["serial_no"]]
        self.assertEqual(held, ["IDU-100", "IDU-101", "IDU-200"])  # oldest GRN first
        self.assertEqual(out["order"]["stage"], "Needs stock")
        # asking again never double-books
        again = self.c.post(f"/api/store/orders/{oid}/reserve").json()
        self.assertEqual(again["reserved"], 0)
        self.assertEqual(self.unit_status("IDU-100"), "Reserved")
        # a second order finds nothing left
        oid2 = self.make_order([self.ac])
        self.assertEqual(self.c.post(f"/api/store/orders/{oid2}/reserve").json()["reserved"], 0)

    def test_bill_gate_and_scan_check_then_dispatch(self):
        self.receive([self.ac_line("100"), self.ac_line("101")], "B1")
        oid = self.make_order([self.ac, self.ac])
        self.as_("keeper")
        self.c.post(f"/api/store/orders/{oid}/reserve")
        order = self.c.get(f"/api/store/orders/{oid}").json()
        self.assertEqual(order["stage"], "Waiting for bill")
        ship = {"scans": ["idu-100", "idu-101"], "courier_id": self.courier.id, "lrn_no": "LR778"}
        r = self.c.post(f"/api/store/orders/{oid}/dispatch", json=ship)
        self.assertEqual(r.status_code, 409)
        self.assertIn("No bill number, no issue", r.json()["detail"])

        self.set_bill(oid)
        self.assertEqual(self.c.get(f"/api/store/orders/{oid}").json()["stage"], "Ready to dispatch")
        r = self.c.post(f"/api/store/orders/{oid}/dispatch", json={**ship, "scans": ["IDU-100"]})
        self.assertEqual(r.status_code, 409)
        self.assertIn("IDU-101", r.json()["detail"])
        r = self.c.post(f"/api/store/orders/{oid}/dispatch", json={**ship, "scans": ["IDU-100", "IDU-101", "IDU-999"]})
        self.assertEqual(r.status_code, 409)
        self.assertIn("IDU-999", r.json()["detail"])
        r = self.c.post(f"/api/store/orders/{oid}/dispatch", json={**ship, "lrn_no": ""})
        self.assertEqual(r.status_code, 400)

        r = self.c.post(f"/api/store/orders/{oid}/dispatch", json=ship)
        self.assertEqual(r.status_code, 200, r.text)
        out = r.json()
        self.assertEqual(out["stage"], "Dispatched")
        self.assertEqual(out["status"], "Shipped")
        self.assertTrue(out["dispatch_no"].startswith("DSP-"))
        self.assertEqual(out["lrn_no"], "LR778")
        self.assertEqual(self.unit_status("IDU-100"), "Issued")

        db = self.Session()
        o = db.get(Order, oid)
        self.assertEqual(o.status, "Shipped")
        self.assertEqual(o.courier_id, self.courier.id)
        serials = sorted((i.serial_no, i.serial_no_2) for i in db.scalars(select(OrderItem).where(OrderItem.order_id == oid)))
        self.assertEqual(serials, [("IDU-100", "ODU-100"), ("IDU-101", "ODU-101")])
        outs = db.scalars(select(StoreLedger).where(StoreLedger.doc_type == "DSP")).all()
        self.assertEqual(sum(x.qty_out for x in outs), 2)
        db.close()

        # a dispatched unit cannot be received again or sent twice
        self.assertEqual(self.c.post(f"/api/store/orders/{oid}/dispatch", json=ship).status_code, 409)
        self.assertEqual(self.c.post("/api/store/serials/check", json={"serial": "IDU-100"}).json()["ok"], False)

    def test_quantity_items_split_the_batch(self):
        self.receive([{"item_id": self.fan.id, "stock_type": "Fresh", "qty": 5}], "B1")
        oid = self.make_order([self.fan, self.fan], bill="INV/1")
        self.as_("keeper")
        self.assertEqual(self.c.post(f"/api/store/orders/{oid}/reserve").json()["reserved"], 2)
        summary = {r["item_code"]: r for r in self.c.get("/api/store/stock").json()}
        self.assertEqual(summary["FAN01"]["available"], 3)
        r = self.c.post(f"/api/store/orders/{oid}/dispatch", json={"scans": [], "courier_id": self.courier.id, "lrn_no": "LR1"})
        self.assertEqual(r.status_code, 200, r.text)
        summary = {r["item_code"]: r for r in self.c.get("/api/store/stock").json()}
        self.assertEqual(summary["FAN01"]["available"], 3)

    def test_release_needs_manager_and_frees_stock(self):
        self.receive([self.ac_line("100")], "B1")
        oid = self.make_order([self.ac])
        self.as_("keeper")
        self.c.post(f"/api/store/orders/{oid}/reserve")
        self.assertEqual(self.c.post(f"/api/store/orders/{oid}/release").status_code, 403)
        self.as_("manager")
        r = self.c.post(f"/api/store/orders/{oid}/release")
        self.assertEqual(r.status_code, 200, r.text)
        self.assertEqual(self.unit_status("IDU-100"), "Available")
        self.assertEqual(r.json()["stage"], "Needs stock")

    def test_cancelling_the_order_releases_the_stock(self):
        self.receive([self.ac_line("100")], "B1")
        oid = self.make_order([self.ac])
        self.as_("keeper")
        self.c.post(f"/api/store/orders/{oid}/reserve")
        self.assertEqual(self.unit_status("IDU-100"), "Reserved")
        self.as_("boss")
        r = self.c.put(f"/api/orders/{oid}", json={"status": "Cancelled"})
        self.assertEqual(r.status_code, 200, r.text)
        self.assertEqual(self.unit_status("IDU-100"), "Available")

    def test_vendor_orders_are_left_alone(self):
        self.receive([self.ac_line("100")], "B1")
        oid = self.make_order([self.ac], fulfilment="Vendor")
        self.as_("keeper")
        self.assertEqual(self.c.post(f"/api/store/orders/{oid}/reserve").status_code, 404)
        self.assertEqual(self.c.get("/api/store/orders").json()["total"], 0)

    def test_permissions(self):
        oid = self.make_order([self.ac])
        self.as_("caller")
        self.assertEqual(self.c.get("/api/store/orders").status_code, 403)
        self.assertEqual(self.c.post(f"/api/store/orders/{oid}/reserve").status_code, 403)
        self.assertEqual(self.c.get("/api/store/lookup/couriers").status_code, 403)
        self.as_("keeper")
        self.assertEqual(self.c.get("/api/store/orders").status_code, 200)
        self.assertEqual([c["courier_name"] for c in self.c.get("/api/store/lookup/couriers").json()], ["BlueDart"])

    def test_order_list_stages_and_counts(self):
        self.receive([self.ac_line("100")], "B1")
        a = self.make_order([self.ac], bill="INV/1")
        b = self.make_order([self.ac])
        self.as_("keeper")
        self.c.post(f"/api/store/orders/{a}/reserve")
        data = self.c.get("/api/store/orders").json()
        self.assertEqual(data["counts"]["Ready to dispatch"], 1)
        self.assertEqual(data["counts"]["Needs stock"], 1)
        only = self.c.get("/api/store/orders", params={"stage": "Ready to dispatch"}).json()
        self.assertEqual([i["id"] for i in only["items"]], [a])
        self.assertNotIn(b, [i["id"] for i in only["items"]])

    def test_creating_a_store_order_needs_no_serials(self):
        self.as_("boss")
        payload = {
            "order_no": "ORD-API-1", "customer_name": "Frost Point", "fulfilment": "Store",
            "items": [{"item_id": self.ac.id, "item_qty": 2, "pcb_warranty_years": 1, "component_warranty_years": 5,
                       "machine_warranty_years": 1, "free_service_count": 0, "dry_free_service_count": 0, "wet_free_service_count": 0}],
        }
        files = {"document": ("po.pdf", io.BytesIO(b"%PDF-1"), "application/pdf")}
        with patch("app.routers.orders.save_upload", return_value="orders/po.pdf"):
            r = self.c.post("/api/orders", data={"payload": json.dumps(payload)}, files=files)
        self.assertEqual(r.status_code, 201, r.text)
        out = r.json()
        self.assertEqual(out["fulfilment"], "Store")
        self.assertEqual(len(out["items"]), 2)
        self.assertEqual(self.c.get("/api/store/orders").json()["total"], 1)

        bad = {**payload, "order_no": "ORD-API-2", "items": [{**payload["items"][0], "serial_no": "IDU-1", "serial_no_2": "ODU-1"}]}
        files = {"document": ("po.pdf", io.BytesIO(b"%PDF-1"), "application/pdf")}
        with patch("app.routers.orders.save_upload", return_value="orders/po.pdf"):
            r = self.c.post("/api/orders", data={"payload": json.dumps(bad)}, files=files)
        self.assertEqual(r.status_code, 400)

    def test_fulfilment_cannot_change_while_stock_is_held(self):
        self.receive([self.ac_line("100")], "B1")
        oid = self.make_order([self.ac])
        self.as_("keeper")
        self.c.post(f"/api/store/orders/{oid}/reserve")
        self.as_("boss")
        r = self.c.put(f"/api/orders/{oid}", json={"fulfilment": "Vendor"})
        self.assertEqual(r.status_code, 409, r.text)


if __name__ == "__main__":
    unittest.main()
