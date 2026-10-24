"""Per-line consignee persistence, permissions, validation and migration coverage."""
from __future__ import annotations

import importlib.util
import os
import sys
import unittest
from datetime import date
from pathlib import Path
from unittest.mock import patch

os.environ.setdefault("MYSQL_DATABASE_URL", "sqlite://")
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, event, inspect, select, text
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool
from alembic.migration import MigrationContext
from alembic.operations import Operations

from app import models  # Register all foreign-key targets.
from app.database import Base, get_db
from app.models.item_master import ItemMaster
from app.models.installation import InstallationRequest
from app.models.order import Order, OrderConsigneeAddress, OrderItem
from app.models.role import Permission, Role
from app.models.user import User
from app.models.vendor import Vendor
from app.routers.orders import router, _clone_order_item_for_serial_row
from app.routers.installations import router as installations_router
from app.security import create_access_token
from app.services.service_serial import order_item_is_installed_for_service


class OrderConsigneeTests(unittest.TestCase):
    def setUp(self):
        # Delivery tests must never send notifications outside the test database.
        for name in ("notify_customer_order_delivered", "notify_vendor_order_update"):
            mocked = patch(f"app.routers.orders.{name}")
            mocked.start()
            self.addCleanup(mocked.stop)
        self.engine = create_engine("sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool)
        event.listen(self.engine, "connect", lambda conn, _: conn.execute("PRAGMA foreign_keys=ON"))
        Base.metadata.create_all(self.engine)
        self.Session = sessionmaker(bind=self.engine, autoflush=False)
        with self.Session() as db:
            self.users = {}
            for role_name in ("admin", "vendor", "service", "engineer"):
                role = Role(name=role_name)
                user = User(name=role_name, email=f"{role_name}@example.com", role=role_name, password_hash="unused", is_active=True)
                db.add_all([role, user])
                db.flush()
                db.add(Permission(role_id=role.id, module="orders", can_view=True, can_edit=role_name == "admin"))
                if role_name == "admin":
                    db.add(Permission(role_id=role.id, module="installations", can_view=True, can_edit=True))
                self.users[role_name] = user.id
            vendor = Vendor(vendor_code="V1", name_of_firm="Own vendor", email="vendor@example.com")
            other_vendor = Vendor(vendor_code="V2", name_of_firm="Other vendor", email="other@example.com")
            master = ItemMaster(item_code="AC", item_name="Air conditioner", serial_count=2)
            db.add_all([vendor, other_vendor, master])
            db.flush()
            order = Order(order_no="O1", order_date=date.today(), vendor_id=vendor.id, status="Delivered", oem_bill_no="OEM1")
            other = Order(order_no="O2", order_date=date.today(), vendor_id=other_vendor.id)
            db.add_all([order, other])
            db.flush()
            self.order_id, self.other_id, self.master_id = order.id, other.id, master.id
            addresses = [
                OrderConsigneeAddress(order_id=order.id, consignee_name="North", address="North address", contact="0123456789", sort_order=0),
                OrderConsigneeAddress(order_id=order.id, consignee_name="South", address="South address", contact="9876543210", sort_order=1),
                OrderConsigneeAddress(order_id=other.id, consignee_name="Other", address="Other address", contact="9000000000", sort_order=0),
            ]
            items = [
                OrderItem(order_id=order.id, item_id=master.id, item_code="AC", serial_no="SER1", serial_no_2="SER1B"),
                OrderItem(order_id=order.id, item_id=master.id, item_code="AC", serial_no="SER2", serial_no_2="SER2B"),
                OrderItem(order_id=other.id, item_id=master.id, item_code="AC", serial_no="OTHER"),
            ]
            db.add_all(addresses + items)
            db.commit()
            self.address_ids = [row.id for row in addresses]
            self.item_ids = [row.id for row in items]

        app = FastAPI()
        app.include_router(router)
        app.include_router(installations_router)

        def get_test_db():
            with self.Session() as db:
                yield db

        app.dependency_overrides[get_db] = get_test_db
        self.client = TestClient(app)

    def tearDown(self):
        self.client.close()
        self.engine.dispose()

    def headers(self, role="admin"):
        token = create_access_token(subject=str(self.users[role]), extra_claims={"role": role})
        return {"Authorization": f"Bearer {token}"}

    def select(self, item=None, address="default", role="admin", order=None):
        if address == "default":
            address = self.address_ids[0]
        return self.client.patch(
            f"/api/orders/{order or self.order_id}/items/{item or self.item_ids[0]}/consignee",
            json={"consignee_address_id": address}, headers=self.headers(role),
        )

    def get_order(self, role="admin"):
        response = self.client.get(f"/api/orders/{self.order_id}", headers=self.headers(role))
        self.assertEqual(response.status_code, 200, response.text)
        return response.json()

    def save_addresses(self, rows, role="admin"):
        return self.client.put(f"/api/orders/{self.order_id}/consignee-addresses", json={"consignee_addresses": rows}, headers=self.headers(role))

    def set_installation_required(self, required, role="admin", order_id=None):
        return self.client.put(f"/api/orders/{order_id or self.order_id}/installation-requirement", json={"installation_required": required}, headers=self.headers(role))

    def exempt_and_deliver(self):
        with self.Session() as db:
            db.get(Order, self.order_id).status = "Pending"
            db.commit()
        response = self.set_installation_required(False)
        self.assertEqual(response.status_code, 200, response.text)
        response = self.client.put(f"/api/orders/{self.order_id}", json={"status": "Delivered"}, headers=self.headers())
        self.assertEqual(response.status_code, 200, response.text)

    def test_installation_is_required_by_default(self):
        order = self.get_order()
        self.assertTrue(order["installation_required"])
        self.assertTrue(all(not item["installation_auto_completed"] for item in order["items"]))

    def test_exempt_order_marks_all_items_installed_only_after_delivery(self):
        with self.Session() as db:
            db.get(Order, self.order_id).status = "Pending"
            db.commit()
        response = self.set_installation_required(False, "vendor")
        self.assertEqual(response.status_code, 200, response.text)
        self.assertTrue(all(item["installation_status"] == "Not Requested" for item in response.json()["items"]))
        response = self.client.put(f"/api/orders/{self.order_id}", json={"status": "Shipped"}, headers=self.headers())
        self.assertEqual(response.status_code, 200, response.text)
        response = self.client.put(f"/api/orders/{self.order_id}", json={"status": "Delivered"}, headers=self.headers("vendor"))
        self.assertEqual(response.status_code, 200, response.text)
        order = self.get_order()
        self.assertFalse(order["installation_required"])
        self.assertEqual(order["status"], "Delivered")
        self.assertTrue(all(item["installation_status"] == "Completed" and item["installation_auto_completed"] for item in order["items"]))
        with self.Session() as db:
            self.assertTrue(order_item_is_installed_for_service(db, db.get(OrderItem, self.item_ids[0])))
            self.assertEqual(db.get(OrderItem, self.item_ids[2]).installation_status, "Not Requested")
            self.assertEqual(db.scalars(select(InstallationRequest)).all(), [])

    def test_delivered_orders_allow_only_admin_to_change_installation_preference(self):
        for role in ("vendor", "service"):
            for required in (True, False):
                response = self.set_installation_required(required, role)
                self.assertEqual(response.status_code, 409, response.text)
        self.assertTrue(self.get_order()["installation_required"])
        response = self.set_installation_required(False, "admin")
        self.assertEqual(response.status_code, 200, response.text)
        self.assertTrue(all(item["installation_auto_completed"] for item in response.json()["items"]))
        response = self.set_installation_required(True, "admin")
        self.assertEqual(response.status_code, 200, response.text)
        self.assertTrue(all(item["installation_status"] == "Not Requested" for item in response.json()["items"]))

    def test_removing_exemption_preserves_genuinely_completed_installations(self):
        self.exempt_and_deliver()
        with self.Session() as db:
            db.get(Order, self.order_id).status = "In Transit"
            db.get(OrderItem, self.item_ids[1]).installation_status = "Completed"
            db.get(OrderItem, self.item_ids[1]).installation_auto_completed = False
            db.commit()
        response = self.set_installation_required(True)
        self.assertEqual(response.status_code, 200, response.text)
        items = self.get_order()["items"]
        self.assertEqual(items[0]["installation_status"], "Not Requested")
        self.assertFalse(items[0]["installation_auto_completed"])
        self.assertEqual(items[1]["installation_status"], "Completed")
        self.assertFalse(items[1]["installation_auto_completed"])

    def test_returned_exempt_order_clears_automatic_installation_and_redelivery_restores_it(self):
        self.exempt_and_deliver()
        response = self.client.put(f"/api/orders/{self.order_id}", json={"status": "Returned"}, headers=self.headers())
        self.assertEqual(response.status_code, 200, response.text)
        self.assertTrue(all(item["installation_status"] == "Not Requested" for item in response.json()["items"]))
        response = self.client.put(f"/api/orders/{self.order_id}", json={"status": "Delivered"}, headers=self.headers())
        self.assertEqual(response.status_code, 200, response.text)
        self.assertTrue(all(item["installation_auto_completed"] for item in response.json()["items"]))

    def test_exemption_permissions_vendor_admin_service_and_order_ownership(self):
        with self.Session() as db:
            db.get(Order, self.order_id).status = "Pending"
            db.commit()
        for role in ("vendor", "admin", "service"):
            response = self.set_installation_required(False, role)
            self.assertEqual(response.status_code, 200, response.text)
            self.assertEqual(self.set_installation_required(True, role).status_code, 200)
        self.assertEqual(self.set_installation_required(False, "vendor", self.other_id).status_code, 404)
        self.assertEqual(self.set_installation_required(False, "engineer").status_code, 403)
        self.assertTrue(self.get_order()["installation_required"])

    def test_active_installation_prevents_exemption_without_mutating_data(self):
        with self.Session() as db:
            db.get(Order, self.order_id).status = "Shipped"
            db.commit()
        self.add_installation()
        response = self.set_installation_required(False)
        self.assertEqual(response.status_code, 409, response.text)
        self.assertTrue(self.get_order()["installation_required"])
        self.assertTrue(all(item["installation_status"] == "Not Requested" for item in self.get_order()["items"]))

    def test_exempt_order_cannot_raise_installation_requests(self):
        self.exempt_and_deliver()
        keys = [f"{self.item_ids[0]}-serial1", f"{self.item_ids[0]}-serial2"]
        response = self.client.post(f"/api/orders/{self.order_id}/submit-serials", json={"order_id": self.order_id, "selected_serials": keys}, headers=self.headers("vendor"))
        self.assertEqual(response.status_code, 400)
        self.assertIn("not required", response.json()["detail"])
        with self.Session() as db:
            role_id = db.scalar(select(Role.id).where(Role.name == "admin"))
            db.scalar(select(Permission).where(Permission.role_id == role_id, Permission.module == "installations")).can_create = True
            db.commit()
        for source in ("vendor", "callcenter"):
            response = self.client.post("/api/installations", json={"source": source, "order_id": self.order_id, "order_item_id": self.item_ids[0], "customer_name": "Customer", "contact_number": "9000000000"}, headers=self.headers())
            self.assertEqual(response.status_code, 400, response.text)
            self.assertIn("not required", response.json()["detail"])

    def test_new_csv_rows_in_exempt_delivered_order_are_automatically_installed(self):
        self.exempt_and_deliver()
        data = "ID,Item Code,Serial Number 1,Serial Number 2\nnew,AC,NEW1,NEW2\n"
        response = self.client.post(f"/api/orders/{self.order_id}/items/import", files={"file": ("items.csv", data, "text/csv")}, headers=self.headers())
        self.assertEqual(response.status_code, 200, response.text)
        items = self.get_order()["items"]
        self.assertEqual(len(items), 3)
        self.assertTrue(all(item["installation_status"] == "Completed" and item["installation_auto_completed"] for item in items))

    def test_installation_preference_status_permissions(self):
        for role in ("admin", "vendor", "service"):
            for status in ("Pending", "Shipped", "In Transit", "Delivered", "Returned", "Cancelled", "Completed"):
                for required in (True, False):
                    with self.subTest(role=role, status=status, required=required):
                        with self.Session() as db:
                            order = db.get(Order, self.order_id)
                            order.status = status
                            order.installation_required = not required
                            db.commit()
                        allowed = role == "admin" or status in {"Pending", "Shipped", "In Transit"}
                        response = self.set_installation_required(required, role)
                        self.assertEqual(response.status_code, 200 if allowed else 409, response.text)
                        self.assertEqual(self.get_order()["installation_required"], required if allowed else not required)

    def test_different_consignees_persist_per_line_and_return_details(self):
        self.assertEqual(self.select().status_code, 200)
        self.assertEqual(self.select(item=self.item_ids[1], address=self.address_ids[1]).status_code, 200)
        items = self.get_order()["items"]
        self.assertEqual([r["consignee_address_id"] for r in items], self.address_ids[:2])
        self.assertEqual(items[0]["consignee"]["address"], "North address")
        self.assertEqual(items[0]["consignee"]["contact"], "0123456789")
        self.assertEqual(items[1]["consignee"]["contact"], "9876543210")
        with self.Session() as db:
            self.assertEqual(db.get(OrderItem, self.item_ids[1]).consignee_address_id, self.address_ids[1])

    def add_installation(self, *, assigned=True, status="Assigned", item_id="default", order_id=None, serial="SER1"):
        with self.Session() as db:
            row = InstallationRequest(
                order_id=order_id or self.order_id,
                order_item_id=self.item_ids[0] if item_id == "default" else item_id,
                customer_name="Customer", contact_number="9000000000", serial_no=serial,
                assigned_engineer=self.users["engineer"] if assigned else None, status=status,
            )
            db.add(row)
            db.commit()
            return row.id

    def test_cancel_resets_only_the_selected_lines_consignee(self):
        self.select()
        self.select(item=self.item_ids[1], address=self.address_ids[1])
        installation_id = self.add_installation()
        response = self.client.post(f"/api/installations/{installation_id}/cancel", headers=self.headers())
        self.assertEqual(response.status_code, 200, response.text)
        order = self.get_order()
        self.assertIsNone(order["items"][0]["consignee_address_id"])
        self.assertIsNone(order["items"][0]["consignee"])
        self.assertFalse(order["items"][0]["consignee_locked"])
        self.assertEqual(order["items"][0]["installation_status"], "Not Requested")
        self.assertEqual(order["items"][1]["consignee_address_id"], self.address_ids[1])
        self.assertEqual(len(order["consignee_addresses"]), 2)
        with self.Session() as db:
            self.assertIsNone(db.get(InstallationRequest, installation_id))

    def test_bulk_cancel_resets_consignee_but_keeps_rows_where_work_started(self):
        self.select()
        self.select(item=self.item_ids[1], address=self.address_ids[1])
        cancelled_id = self.add_installation()
        retained_id = self.add_installation(item_id=self.item_ids[1], serial="SER2", status="In Progress")
        response = self.client.post("/api/installations/bulk-cancel", json={"installation_ids": [cancelled_id, retained_id]}, headers=self.headers())
        self.assertEqual(response.status_code, 200, response.text)
        self.assertEqual(response.json()["cancelled"], [cancelled_id])
        items = self.get_order()["items"]
        self.assertIsNone(items[0]["consignee_address_id"])
        self.assertFalse(items[0]["consignee_locked"])
        self.assertEqual(items[1]["consignee_address_id"], self.address_ids[1])
        self.assertTrue(items[1]["consignee_locked"])

    def test_engineer_assignment_locks_only_its_line_for_all_editing_roles(self):
        self.select()
        self.add_installation()
        for role in ("admin", "vendor", "service"):
            with self.subTest(role=role):
                items = self.get_order(role)["items"]
                self.assertTrue(items[0]["consignee_locked"])
                self.assertFalse(items[1]["consignee_locked"])
                response = self.select(role=role, address=self.address_ids[1])
                self.assertEqual(response.status_code, 409, response.text)
                self.assertIn("engineer", response.json()["detail"])
                self.assertEqual(self.select(role=role, address=None).status_code, 409)
                self.assertEqual(self.select(role=role, item=self.item_ids[1], address=self.address_ids[1]).status_code, 200)
        self.assertEqual(self.get_order()["items"][0]["consignee_address_id"], self.address_ids[0])

    def test_submission_without_engineer_assignment_does_not_lock_consignee(self):
        self.add_installation(assigned=False, status="Submitted")
        self.assertFalse(self.get_order()["items"][0]["consignee_locked"])
        self.assertEqual(self.select().status_code, 200)

    def test_installation_detail_returns_only_its_lines_selected_consignee(self):
        self.select()
        self.select(item=self.item_ids[1], address=self.address_ids[1])
        installation_id = self.add_installation(assigned=False, status="Submitted")
        response = self.client.get(f"/api/installations/{installation_id}", headers=self.headers())
        self.assertEqual(response.status_code, 200, response.text)
        consignee = response.json()["consignee"]
        self.assertEqual(consignee["id"], self.address_ids[0])
        self.assertEqual(consignee["consignee_name"], "North")
        self.assertEqual(consignee["address"], "North address")
        self.assertEqual(consignee["contact"], "0123456789")

    def test_installation_detail_without_consignee_is_valid(self):
        for item_id in (self.item_ids[0], None):
            with self.subTest(item_id=item_id):
                installation_id = self.add_installation(assigned=False, status="Submitted", item_id=item_id)
                response = self.client.get(f"/api/installations/{installation_id}", headers=self.headers())
                self.assertEqual(response.status_code, 200, response.text)
                self.assertIsNone(response.json()["consignee"])

    def test_installation_submission_does_not_require_a_consignee(self):
        keys = [f"{self.item_ids[0]}-serial1", f"{self.item_ids[0]}-serial2"]
        response = self.client.post(f"/api/orders/{self.order_id}/submit-serials", json={"order_id": self.order_id, "selected_serials": keys}, headers=self.headers("vendor"))
        self.assertEqual(response.status_code, 200, response.text)

    def test_lock_persists_after_assigned_work_is_completed(self):
        self.select()
        self.add_installation(status="Completed")
        self.assertTrue(self.get_order()["items"][0]["consignee_locked"])
        self.assertEqual(self.select(address=self.address_ids[1]).status_code, 409)

    def test_legacy_assignment_matches_serial_within_the_same_order_only(self):
        self.add_installation(item_id=None, order_id=self.other_id)
        self.assertFalse(self.get_order()["items"][0]["consignee_locked"])
        self.add_installation(item_id=None, serial=" ser1b ")
        self.assertTrue(self.get_order()["items"][0]["consignee_locked"])
        self.assertEqual(self.select().status_code, 409)

    def test_vendor_can_edit_own_order_at_any_status_but_not_another_vendor(self):
        for status in ("Pending", "Shipped", "Delivered", "Completed"):
            with self.Session() as db:
                db.get(Order, self.order_id).status = status
                db.commit()
            response = self.select(role="vendor")
            self.assertEqual(response.status_code, 200, response.text)
        self.assertEqual(self.select(role="vendor", order=self.other_id, item=self.item_ids[2], address=self.address_ids[2]).status_code, 404)
        self.assertEqual(self.select(role="vendor", item=self.item_ids[2]).status_code, 404)
        rows = self.get_order("vendor")["consignee_addresses"]
        rows[0]["address"] = "Vendor updated address"
        self.assertEqual(self.save_addresses(rows, "vendor").status_code, 200)

    def test_service_can_edit_with_view_permission_but_cannot_bypass_access_revocation(self):
        self.assertEqual(self.select(role="service").status_code, 200)
        rows = self.get_order("service")["consignee_addresses"]
        rows[0]["contact"] = "1112223334"
        self.assertEqual(self.save_addresses(rows, "service").status_code, 200)
        with self.Session() as db:
            role = db.scalar(select(Role).where(Role.name == "service"))
            db.scalar(select(Permission).where(Permission.role_id == role.id)).can_view = False
            db.commit()
        self.assertEqual(self.select(role="service").status_code, 404)

    def test_other_roles_and_cross_order_addresses_are_rejected(self):
        self.assertEqual(self.select(role="engineer").status_code, 403)
        self.assertEqual(self.save_addresses([], "engineer").status_code, 403)
        self.assertEqual(self.select(address=self.address_ids[2]).status_code, 400)
        response = self.save_addresses([{"id": self.address_ids[2], "consignee_name": "Other", "address": "Other", "contact": "9000000000"}])
        self.assertEqual(response.status_code, 400)
        self.assertIsNone(self.get_order()["items"][0]["consignee_address_id"])

    def test_exactly_ten_ascii_digits_are_required(self):
        for contact in (None, "", "123456789", "12345678901", "12345abcde", "１２３４５６７８９０", "123 456789", "+123456789", "1234567890 "):
            with self.subTest(contact=contact):
                response = self.save_addresses([{"consignee_name": "Test", "address": "Address", "contact": contact}])
                self.assertEqual(response.status_code, 400, response.text)
                self.assertIn("Mobile number", response.json()["detail"])
        self.assertEqual(len(self.get_order()["consignee_addresses"]), 2)

    def test_name_and_address_required_and_valid_mobile_can_start_with_zero(self):
        for name, address in (("", "Address"), ("Name", "")):
            self.assertEqual(self.save_addresses([{"consignee_name": name, "address": address, "contact": "0123456789"}]).status_code, 400)
        response = self.save_addresses([{"consignee_name": "New", "address": "New address", "contact": "0123456789"}])
        self.assertEqual(response.status_code, 200, response.text)
        self.assertEqual(response.json()["consignee_addresses"][0]["contact"], "0123456789")

    def test_address_edits_keep_ids_and_selected_rows_and_removal_is_protected(self):
        self.select()
        rows = self.get_order()["consignee_addresses"]
        rows[0]["address"] = "Updated North"
        response = self.save_addresses(list(reversed(rows)))
        self.assertEqual(response.status_code, 200, response.text)
        item = self.get_order()["items"][0]
        self.assertEqual(item["consignee_address_id"], self.address_ids[0])
        self.assertEqual(item["consignee"]["address"], "Updated North")
        self.assertEqual(self.save_addresses([rows[1]]).status_code, 409)
        self.assertEqual(self.select(address=None).status_code, 200)
        self.assertIsNone(self.get_order()["items"][0]["consignee"])
        self.assertEqual(self.save_addresses([rows[1]]).status_code, 200)

    def test_legacy_invalid_consignee_cannot_be_selected(self):
        with self.Session() as db:
            db.get(OrderConsigneeAddress, self.address_ids[0]).contact = None
            db.commit()
        response = self.select()
        self.assertEqual(response.status_code, 400)
        self.assertIn("Mobile number is required", response.json()["detail"])

    def test_regular_order_edit_preserves_consignee_ids_and_line_selections(self):
        self.select()
        rows = self.get_order()["consignee_addresses"]
        rows[0]["address"] = "Edited through order form"
        response = self.client.put(f"/api/orders/{self.order_id}", json={"consignee_addresses": rows}, headers=self.headers())
        self.assertEqual(response.status_code, 200, response.text)
        item = self.get_order()["items"][0]
        self.assertEqual(item["consignee_address_id"], self.address_ids[0])
        self.assertEqual(item["consignee"]["address"], "Edited through order form")

    def test_serial_pair_cannot_mix_consignees(self):
        self.select()
        self.select(item=self.item_ids[1], address=self.address_ids[1])
        keys = [f"{self.item_ids[0]}-serial1", f"{self.item_ids[1]}-serial2"]
        response = self.client.post(f"/api/orders/{self.order_id}/submit-serials", json={"order_id": self.order_id, "selected_serials": keys}, headers=self.headers("vendor"))
        self.assertEqual(response.status_code, 400)
        self.assertIn("same consignee", response.json()["detail"])
        self.assertEqual(len(self.get_order()["items"]), 2)

    def test_duplicate_ids_and_unrelated_changes_are_rejected(self):
        row = self.get_order()["consignee_addresses"][0]
        self.assertEqual(self.save_addresses([row, row]).status_code, 400)
        url = f"/api/orders/{self.order_id}/items/{self.item_ids[0]}/consignee"
        response = self.client.patch(url, json={"consignee_address_id": self.address_ids[0], "item_code": "TAMPER"}, headers=self.headers("vendor"))
        self.assertEqual(response.status_code, 422)
        self.assertEqual(self.client.patch(url, json={}, headers=self.headers()).status_code, 422)

    def test_serial_submission_preserves_consignees_without_pairing_different_addresses(self):
        self.select()
        self.select(item=self.item_ids[1], address=self.address_ids[1])
        keys = [f"{self.item_ids[0]}-serial1", f"{self.item_ids[1]}-serial2", f"{self.item_ids[1]}-serial1", f"{self.item_ids[0]}-serial2"]
        response = self.client.post(f"/api/orders/{self.order_id}/submit-serials", json={"order_id": self.order_id, "selected_serials": keys}, headers=self.headers("vendor"))
        self.assertEqual(response.status_code, 200, response.text)
        items = self.get_order()["items"]
        self.assertEqual(len(items), 2)
        by_serial = {serial: row["consignee_address_id"] for row in items for serial in (row["serial_no"], row["serial_no_2"])}
        self.assertEqual(by_serial, {"SER1": self.address_ids[0], "SER1B": self.address_ids[0], "SER2": self.address_ids[1], "SER2B": self.address_ids[1]})

    def test_csv_clones_keep_the_selection(self):
        self.select()
        with self.Session() as db:
            row = _clone_order_item_for_serial_row(db.get(OrderItem, self.item_ids[0]))
            self.assertEqual(row.consignee_address_id, self.address_ids[0])

    def test_vendor_pending_line_replacement_preserves_consignees(self):
        with self.Session() as db:
            db.get(Order, self.order_id).status = "Pending"
            db.commit()
        items = [{"item_id": self.master_id, "consignee_address_id": address, "item_qty": 1,
                  "pcb_warranty_years": 1, "component_warranty_years": 1, "machine_warranty_years": 1,
                  "dry_free_service_count": 0, "wet_free_service_count": 0} for address in self.address_ids[:2]]
        response = self.client.put(f"/api/orders/{self.order_id}/vendor-line-items", json={"items": items}, headers=self.headers("vendor"))
        self.assertEqual(response.status_code, 200, response.text)
        self.assertEqual([r["consignee_address_id"] for r in response.json()["items"]], self.address_ids[:2])


class OrderConsigneeMigrationTests(unittest.TestCase):
    def test_installation_exemption_migration_defaults_and_downgrade(self):
        path = Path(__file__).resolve().parents[1] / "alembic/versions/0083_order_installation_required.py"
        spec = importlib.util.spec_from_file_location("installation_policy_migration", path)
        migration = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(migration)
        engine = create_engine("sqlite://")
        with engine.begin() as conn:
            conn.execute(text("CREATE TABLE orders (id INTEGER PRIMARY KEY)"))
            conn.execute(text("CREATE TABLE order_items (id INTEGER PRIMARY KEY, installation_status VARCHAR(50))"))
            conn.execute(text("INSERT INTO orders VALUES (1)"))
            conn.execute(text("INSERT INTO order_items VALUES (1, 'Not Requested')"))
            with patch.object(migration, "op", Operations(MigrationContext.configure(conn))):
                migration.upgrade()
                self.assertEqual(conn.execute(text("SELECT installation_required FROM orders")).scalar(), 1)
                self.assertEqual(conn.execute(text("SELECT installation_auto_completed FROM order_items")).scalar(), 0)
                migration.downgrade()
            self.assertEqual(conn.execute(text("SELECT installation_status FROM order_items")).scalar(), "Not Requested")
            self.assertEqual(conn.execute(text("SELECT id FROM orders")).scalar(), 1)
        engine.dispose()

    def test_upgrade_and_downgrade_preserve_existing_order_rows(self):
        path = Path(__file__).resolve().parents[1] / "alembic/versions/0082_order_item_consignee.py"
        spec = importlib.util.spec_from_file_location("consignee_migration", path)
        migration = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(migration)
        engine = create_engine("sqlite://")
        with engine.begin() as conn:
            conn.execute(text("CREATE TABLE order_consignee_addresses (id INTEGER PRIMARY KEY)"))
            conn.execute(text("CREATE TABLE order_items (id INTEGER PRIMARY KEY, item_code VARCHAR(100))"))
            conn.execute(text("INSERT INTO order_items VALUES (1, '8908012210924')"))
            with patch.object(migration, "op", Operations(MigrationContext.configure(conn))):
                migration.upgrade()
                self.assertIn("consignee_address_id", {c["name"] for c in inspect(conn).get_columns("order_items")})
                self.assertEqual(conn.execute(text("SELECT consignee_address_id FROM order_items")).scalar(), None)
                migration.downgrade()
            self.assertNotIn("consignee_address_id", {c["name"] for c in inspect(conn).get_columns("order_items")})
            self.assertEqual(conn.execute(text("SELECT item_code FROM order_items")).scalar(), "8908012210924")
        engine.dispose()


if __name__ == "__main__":
    unittest.main()
