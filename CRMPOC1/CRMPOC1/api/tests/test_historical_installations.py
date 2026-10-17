from __future__ import annotations

import os
import sys
import tempfile
import unittest
from datetime import date
from pathlib import Path

os.environ.setdefault("MYSQL_DATABASE_URL", "sqlite://")
os.environ.setdefault("UPLOAD_DIR", str(Path(tempfile.mkdtemp(prefix="indcool_historical_")) / "uploads"))
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from fastapi.testclient import TestClient
from sqlalchemy import create_engine, func, select
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.database import Base, get_db
from app.main import app
from app.models import HistoricalInstallationCompletion, Order, OrderItem, PaymentTransaction, User
from app.models.installation import InstallationRequest, InstallationStatusLog
from app.models.role import Permission, Role
from app.models.serial_history import SerialHistoryEvent
from app.security import create_access_token, hash_password
from app.seed import seed_roles


class HistoricalInstallationTests(unittest.TestCase):
    def setUp(self):
        engine = create_engine("sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool)
        Base.metadata.create_all(engine)
        self.Session = sessionmaker(bind=engine, autoflush=False, autocommit=False, future=True)
        self.db = self.Session()
        seed_roles(self.db)

        def override():
            session = self.Session()
            try:
                yield session
            finally:
                session.close()

        app.dependency_overrides[get_db] = override
        self.client = TestClient(app)
        self.admin = self._user("admin@historical.test", "admin")
        self.engineer = self._user("engineer@historical.test", "engineer")
        self.service_manager = self._user("manager@historical.test", "service_manager")
        self.order = Order(order_no="GEMC-HIST-001", order_date=date(2024, 1, 1), status="Delivered",
                           customer_name="Historical Customer", customer_contact="9999999999")
        self.db.add(self.order)
        self.db.flush()
        self.existing_item = OrderItem(order_id=self.order.id, item_code="ITEM-1", serial_no="SER-H-1", installation_status="Submitted")
        self.new_item = OrderItem(order_id=self.order.id, item_code="ITEM-2", serial_no="SER-H-2", serial_no_2="SER-H-2B")
        self.missing_item = OrderItem(order_id=self.order.id, item_code="ITEM-3")
        self.db.add_all([self.existing_item, self.new_item, self.missing_item])
        self.db.flush()
        self.existing_request = InstallationRequest(
            source="vendor", order_id=self.order.id, order_item_id=self.existing_item.id,
            customer_name="Historical Customer", contact_number="9999999999", status="Payment Pending",
            payment_amount_requested=80, payment_type_requested="Cash", serial_no="SER-H-1",
        )
        self.db.add(self.existing_request)
        self.db.commit()

    def tearDown(self):
        app.dependency_overrides.clear()
        self.db.close()

    def _user(self, email, role):
        user = User(name=email.split("@")[0], email=email, password_hash=hash_password("password123"), role=role, is_active=True)
        self.db.add(user)
        self.db.flush()
        return user

    def _headers(self, user):
        return {"Authorization": f"Bearer {create_access_token(subject=str(user.id), extra_claims={'role': user.role})}"}

    def test_permission_preview_completion_audit_and_idempotency(self):
        denied = self.client.get("/api/historical-installations/search", params={"q": "GEMC"}, headers=self._headers(self.engineer))
        self.assertEqual(denied.status_code, 403, denied.text)

        engineer_role = self.db.scalar(select(Role).where(func.lower(Role.name) == "engineer"))
        self.db.add(Permission(role_id=engineer_role.id, module="historical_installations", can_view=True, can_edit=False))
        self.db.commit()
        view_only = self.client.get("/api/historical-installations/search", params={"q": "GEMC"}, headers=self._headers(self.engineer))
        self.assertEqual(view_only.status_code, 200, view_only.text)

        search = self.client.get("/api/historical-installations/search", params={"q": "GEMC-HIST"}, headers=self._headers(self.admin))
        self.assertEqual(search.status_code, 200, search.text)
        self.assertEqual(search.json()[0]["order_id"], self.order.id)
        preview = self.client.get(f"/api/historical-installations/{self.order.id}/preview", headers=self._headers(self.admin))
        self.assertEqual(preview.status_code, 200, preview.text)
        body = preview.json()
        self.assertEqual(body["summary"]["requests_to_create"], 1)
        self.assertEqual(body["summary"]["requests_to_complete"], 1)
        self.assertEqual(body["summary"]["missing_serial_items"], 1)

        payload = {
            "order_id": self.order.id, "preview_token": body["preview_token"], "operation_key": "operation-001",
            "installation_date": "2024-02-10", "reason": "Imported historical completion",
            "payment_total": 100.01, "payment_type": "Cash",
        }
        cannot_complete = self.client.post("/api/historical-installations/complete", data={"payload": __import__("json").dumps(payload)}, headers=self._headers(self.engineer))
        self.assertEqual(cannot_complete.status_code, 403, cannot_complete.text)
        completed = self.client.post("/api/historical-installations/complete", data={"payload": __import__("json").dumps(payload)}, headers=self._headers(self.admin))
        self.assertEqual(completed.status_code, 200, completed.text)
        result = completed.json()
        self.assertEqual((result["created_count"], result["completed_count"], result["incomplete_count"]), (1, 1, 1))

        self.db.expire_all()
        self.assertEqual(self.db.get(Order, self.order.id).status, "Completed")
        self.assertEqual(self.db.get(OrderItem, self.existing_item.id).installation_status, "Completed")
        self.assertEqual(self.db.get(OrderItem, self.new_item.id).installation_status, "Completed")
        self.assertEqual(self.db.get(OrderItem, self.missing_item.id).installation_status, "Not Requested")
        requests = list(self.db.scalars(select(InstallationRequest).where(InstallationRequest.order_id == self.order.id).order_by(InstallationRequest.id)))
        self.assertEqual(len(requests), 2)
        self.assertEqual({row.status for row in requests}, {"Completed"})
        self.assertEqual([float(row.payment_amount_paid) for row in requests], [50.01, 50.0])
        self.assertEqual(self.db.scalar(select(PaymentTransaction).where(PaymentTransaction.id == result["payment_transaction_id"])).request_count, 2)
        audit = self.db.scalar(select(HistoricalInstallationCompletion).where(HistoricalInstallationCompletion.operation_key == "operation-001"))
        self.assertEqual((audit.created_count, audit.completed_count, audit.incomplete_count), (1, 1, 1))
        self.assertEqual(audit.payment_transaction_id, result["payment_transaction_id"])
        self.assertEqual(len(list(self.db.scalars(select(InstallationStatusLog)))), 2)
        self.assertEqual(len(list(self.db.scalars(select(SerialHistoryEvent).where(SerialHistoryEvent.source_id == audit.id)))), 2)

        again = self.client.post("/api/historical-installations/complete", data={"payload": __import__("json").dumps(payload)}, headers=self._headers(self.admin))
        self.assertEqual(again.status_code, 200, again.text)
        self.assertTrue(again.json()["idempotent"])
        self.assertEqual(self.db.scalar(select(__import__("sqlalchemy").func.count()).select_from(PaymentTransaction)), 1)

    def test_service_manager_uses_its_own_role_permission(self):
        manager_role = self.db.scalar(select(Role).where(func.lower(Role.name) == "service_manager"))
        self.db.add(Permission(role_id=manager_role.id, module="historical_installations", can_view=True, can_edit=True))
        self.db.commit()
        visible = self.client.get("/api/historical-installations/search", params={"q": "GEMC"}, headers=self._headers(self.service_manager))
        self.assertEqual(visible.status_code, 200, visible.text)


if __name__ == "__main__":
    unittest.main()
