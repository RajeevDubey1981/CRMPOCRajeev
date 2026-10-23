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
from app.models.item_master import ItemMaster
from app.models.order import Order, OrderItem
from app.models.service import ServiceRequest, ServiceRequestItem, ServiceRequestUnit
from app.security import create_access_token, hash_password
from app.seed import seed_roles


class OrderAssignedOnceTests(unittest.TestCase):
    """The same order serial cannot be given to two people through two service requests (this happened live: one request
    went to Vikash Bhati and a second one, for the same two serials, to Jayveer Singh)."""

    def setUp(self):
        engine = create_engine("sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool)
        Base.metadata.create_all(engine)
        self.Session = sessionmaker(bind=engine, autoflush=False, autocommit=False, future=True)
        self.db = self.Session()
        seed_roles(self.db)
        self.manager = self._user("mgr@t.com", "service_manager", "Service Manager")
        self.vikash = self._user("vikash@t.com", "service", "Vikash Bhati")
        self.jayveer = self._user("jayveer@t.com", "service", "Jayveer Singh")
        master = ItemMaster(item_code="WAC", item_name="WAC", serial_count=1)
        self.db.add(master)
        self.db.flush()
        order = Order(order_no="GEMC-1", order_date=__import__("datetime").date(2026, 10, 1), customer_name="Bank", customer_contact="9000000000")
        self.db.add(order)
        self.db.flush()
        self.item = OrderItem(order_id=order.id, item_id=master.id, item_code="WAC", serial_no="SER-1")
        self.db.add(self.item)
        self.db.flush()
        self.first = self._service("SRV_1", order.id)
        self.second = self._service("SRV_2", order.id)
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

    def _user(self, email, role, name):
        u = User(name=name, email=email, password_hash=hash_password("pw123456"), role=role, is_active=True)
        self.db.add(u)
        self.db.flush()
        return u

    def _service(self, no, order_id, status_="New"):
        s = ServiceRequest(request_no=no, status=status_, customer_name="Bank", customer_mobile="9000000000", order_id=order_id, order_item_id=self.item.id, serial_no="SER-1")
        self.db.add(s)
        self.db.flush()
        sri = ServiceRequestItem(service_request_id=s.id, order_id=order_id, item_code="WAC", ordered_quantity=1, serial_count=1)
        self.db.add(sri)
        self.db.flush()
        self.db.add(ServiceRequestUnit(service_request_id=s.id, service_request_item_id=sri.id, order_item_id=self.item.id, serial_no="SER-1"))
        return s.id

    def h(self, user):
        return {"Authorization": f"Bearer {create_access_token(subject=str(user.id), extra_claims={'role': user.role})}"}

    def assign(self, sid, user):
        return self.client.post(f"/api/services/{sid}/assign-service-user", json={"service_user_id": user.id}, headers=self.h(self.manager))

    def test_the_second_request_for_the_same_order_cannot_go_to_another_person(self):
        self.assertEqual(self.assign(self.first, self.vikash).status_code, 200)
        r = self.assign(self.second, self.jayveer)
        self.assertEqual(r.status_code, 409, r.text)
        self.assertIn("The same order cannot be assigned twice", r.json()["detail"])
        self.assertIn("SRV_1", r.json()["detail"])
        self.assertIn("Vikash Bhati", r.json()["detail"])
        self.assertIn("GEMC-1", r.json()["detail"])
        with self.Session() as s:
            self.assertIsNone(s.get(ServiceRequest, self.second).assigned_service_user_id, "nothing was assigned")

    def test_the_same_request_can_still_be_reassigned(self):
        self.assign(self.first, self.vikash)
        self.assertEqual(self.assign(self.first, self.jayveer).status_code, 200)

    def test_once_the_first_is_closed_the_order_can_be_serviced_again(self):
        self.assign(self.first, self.vikash)
        with self.Session() as s:
            s.get(ServiceRequest, self.first).status = "Closed"
            s.commit()
        self.assertEqual(self.assign(self.second, self.jayveer).status_code, 200)

    def test_an_unassigned_other_request_does_not_block(self):
        self.assertEqual(self.assign(self.second, self.jayveer).status_code, 200)

    def test_assigning_an_engineer_to_the_same_serial_is_refused_too(self):
        engineer = self._user("eng@t.com", "engineer", "Engineer One")
        self.db.commit()
        self.assign(self.first, self.vikash)
        with self.Session() as s:
            unit_id = s.scalar(__import__("sqlalchemy").select(ServiceRequestUnit.id).where(ServiceRequestUnit.service_request_id == self.second))
        r = self.client.post(f"/api/services/{self.second}/assign-units", json={"unit_ids": [unit_id], "engineer_id": engineer.id}, headers=self.h(self.manager))
        self.assertEqual(r.status_code, 409, r.text)
        self.assertIn("cannot be assigned twice", r.json()["detail"])


if __name__ == "__main__":
    unittest.main()
