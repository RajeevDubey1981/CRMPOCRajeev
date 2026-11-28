from __future__ import annotations

import os
import sys
import unittest
from datetime import date
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
from app.models.complaint import Complaint
from app.models.role import Permission, Role
from app.models.web_order import WebOrder, WebOrderEvent, WebOrderItem, WebOrderPayment
from app.security import create_access_token, hash_password
from app.seed import seed_roles

KEY = "test-web-orders-key"


def site_order(**over):
    o = {
        "id": 244, "order_number": "ORD-ABC123", "user_id": 7, "full_name": "Ravi Kumar", "email": "ravi@example.com", "mobile": "+91 98915 72565",
        "shipping_address": "12 MG Road, Noida 201301", "billing_address": "12 MG Road, Noida 201301", "gst_number": None, "company_name": None,
        "coupon_code": "SAVE5", "discount_amount": "500.00", "subtotal": "18000.00", "shipping": "0.00", "tax": "3290.82", "total": "18288.82",
        "status": "pending", "payment_status": "pending", "payment_method": "razorpay", "razorpay_order_id": "order_X1", "payment_id": None,
        "created_at": "2026-11-15 08:16:19", "updated_at": "2026-11-15 08:16:19", "some_new_site_column": "kept",
        "items": [{"id": 1, "product_id": "IDCACSBF18K3F", "product_name": "1.5 Ton 3 Star Inverter Split AC", "product_info": {"color": "white"}, "price": "18000.00", "quantity": 1, "delivery_date": None, "time_slot": None}],
        "addresses": [{"id": 1, "type": "shipping", "full_name": "Ravi Kumar", "mobile": "9891572565", "address_line1": "12 MG Road", "city": "Noida", "state": "Uttar Pradesh", "pincode": "201301", "country": "India"}],
        "payments": [{"id": 1, "razorpay_order_id": "order_X1", "payment_id": None, "status": "created", "amount": "18288.82", "currency": "INR", "attempted_at": "2026-11-15 08:16:30", "response": "{}"}],
    }
    o.update(over)
    return o


class WebOrderTests(unittest.TestCase):
    def setUp(self):
        self._patch = mock.patch.object(settings, "web_orders_ingest_key", KEY)
        self._patch.start()
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
        self._patch.stop()

    def h(self, user):
        return {"Authorization": f"Bearer {create_access_token(str(user.id))}"}

    def send(self, *orders, key=KEY):
        return self.client.post("/api/web-orders/ingest", json={"orders": list(orders)}, headers={"X-Web-Orders-Key": key} if key else {})

    # --- the sync door ---
    def test_the_sync_needs_the_right_key_and_can_be_switched_off(self):
        self.assertEqual(self.send(site_order(), key=None).status_code, 401)
        self.assertEqual(self.send(site_order(), key="wrong").status_code, 401)
        with mock.patch.object(settings, "web_orders_ingest_key", ""):
            self.assertEqual(self.send(site_order(), key="anything").status_code, 503)
        self.assertEqual(self.db.query(WebOrder).count(), 0)

    def test_an_order_arrives_with_items_addresses_payments_and_a_placed_event(self):
        r = self.send(site_order())
        self.assertEqual(r.status_code, 200, r.text)
        self.assertEqual(r.json()["created"], 1)
        self.db.expire_all()
        o = self.db.query(WebOrder).one()
        self.assertEqual((o.order_number, o.customer_name, o.mobile10, float(o.total)), ("ORD-ABC123", "Ravi Kumar", "9891572565", 18288.82))
        self.assertIn("some_new_site_column", o.extra_json)
        self.assertEqual(self.db.query(WebOrderItem).count(), 1)
        self.assertEqual(self.db.query(WebOrderPayment).count(), 1)
        self.assertEqual([e.kind for e in self.db.query(WebOrderEvent).order_by(WebOrderEvent.id)], ["placed", "payment_status"])

    def test_sending_it_again_changes_nothing_but_a_new_status_adds_to_the_timeline(self):
        self.send(site_order())
        self.send(site_order())
        self.assertEqual(self.db.query(WebOrder).count(), 1)
        self.assertEqual(self.db.query(WebOrderItem).count(), 1)
        self.assertEqual(self.db.query(WebOrderEvent).count(), 2)
        r = self.send(site_order(status="cancelled", payment_status="failed", updated_at="2026-11-16 10:00:00"))
        self.assertEqual(r.json()["updated"], 1)
        self.db.expire_all()
        events = [(e.kind, e.old_value, e.new_value) for e in self.db.query(WebOrderEvent).order_by(WebOrderEvent.id)]
        self.assertIn(("status", "pending", "cancelled"), events)
        self.assertIn(("payment_status", "pending", "failed"), events)
        self.assertEqual(self.db.query(WebOrder).one().status, "cancelled")

    def test_one_bad_order_does_not_stop_the_others(self):
        r = self.send({"order_number": "no id"}, site_order(id=300, order_number="ORD-OK"))
        body = r.json()
        self.assertEqual((body["created"], body["failed"]), (1, 1))
        self.assertEqual(self.db.query(WebOrder).filter(WebOrder.order_number == "ORD-OK").count(), 1)

    # --- who may see it ---
    def test_only_roles_with_the_tick_can_open_web_orders(self):
        self.send(site_order())
        self.assertEqual(self.client.get("/api/web-orders", headers=self.h(self.eng)).status_code, 403)
        self.assertEqual(self.client.get("/api/web-orders/summary", headers=self.h(self.eng)).status_code, 403)
        self.assertEqual(self.client.get("/api/web-orders", headers=self.h(self.admin)).status_code, 200)
        role = self.db.scalar(select(Role).where(Role.name == "engineer"))
        self.db.add(Permission(role_id=role.id, module="web_orders", sub_module=None, can_view=True, can_create=False, can_edit=False, can_delete=False, can_export=False))
        self.db.commit()
        r = self.client.get("/api/web-orders", headers=self.h(self.eng))
        self.assertEqual(r.status_code, 200, r.text)
        self.assertEqual(self.client.get("/api/web-orders/export", headers=self.h(self.eng)).status_code, 403)  # view is not export

    def test_the_list_filters_and_the_summary_counts(self):
        self.send(site_order(), site_order(id=245, order_number="ORD-2", status="cancelled", payment_status="failed", full_name="Sita Devi", mobile="9000000000", email="sita@example.com"))
        r = self.client.get("/api/web-orders?status=cancelled", headers=self.h(self.admin)).json()
        self.assertEqual([x["order_number"] for x in r["items"]], ["ORD-2"])
        r = self.client.get("/api/web-orders?q=Ravi", headers=self.h(self.admin)).json()
        self.assertEqual(r["total"], 1)
        s = self.client.get("/api/web-orders/summary", headers=self.h(self.admin)).json()
        self.assertEqual((s["total"], s["by_status"]["cancelled"], s["by_status"]["pending"], s["sync_enabled"]), (2, 1, 1, True))
        self.assertIsNotNone(s["last_synced_at"])
        self.assertIsNotNone(s["heartbeat_at"])

    def test_an_empty_send_still_counts_as_the_sync_being_alive(self):
        self.assertIsNone(self.client.get("/api/web-orders/summary", headers=self.h(self.admin)).json()["heartbeat_at"])
        self.assertEqual(self.send().status_code, 200)
        self.assertIsNotNone(self.client.get("/api/web-orders/summary", headers=self.h(self.admin)).json()["heartbeat_at"])

    def test_the_detail_shows_everything_and_the_customers_complaints(self):
        self.send(site_order())
        self.db.add(Complaint(comp_no="IDC_9", comp_date=date.today(), customer_name="Ravi", customer_mobile="9891572565", query_type="Service", status="Pending", access_code="1"))
        self.db.commit()
        oid = self.db.query(WebOrder).one().id
        d = self.client.get(f"/api/web-orders/{oid}", headers=self.h(self.admin)).json()
        self.assertEqual(d["order"]["status"], "pending")
        self.assertEqual(d["items"][0]["product_info"], {"color": "white"})
        self.assertEqual(d["addresses"][0]["pincode"], "201301")
        self.assertEqual(d["payments"][0]["status"], "created")
        self.assertEqual([e["kind"] for e in d["events"]], ["placed", "payment_status"])
        self.assertEqual([c["comp_no"] for c in d["complaints"]], ["IDC_9"])
        self.assertEqual(d["order"]["extra"], {"some_new_site_column": "kept"})


if __name__ == "__main__":
    unittest.main()
