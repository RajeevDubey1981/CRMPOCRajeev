from __future__ import annotations

import os
import sys
import unittest
from datetime import date
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
from app.models.installation import InstallationRequest
from app.models.order import Order, OrderItem
from app.security import create_access_token, hash_password
from app.seed import seed_roles
from app.services.installation_stages import STAGES, STAGE_OF, stage_counts


class InstallationStageTests(unittest.TestCase):
    """The installation screens and the dashboard filter by stage: Not assigned, Assigned, In progress, Installed ..."""

    def setUp(self):
        engine = create_engine("sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool)
        Base.metadata.create_all(engine)
        self.Session = sessionmaker(bind=engine, autoflush=False, autocommit=False, future=True)
        self.db = self.Session()
        seed_roles(self.db)
        self.admin = self._user("admin@t.com", "admin")
        self.eng = self._user("eng@t.com", "engineer")
        self.eng2 = self._user("eng2@t.com", "engineer")
        for status_, engineer in (
            ("Pending", None), ("Submitted", None), ("Assigned", self.eng), ("Assigned", self.eng2), ("In Progress", self.eng),
            ("Serial Pending Verification", self.eng), ("Installation Completed", self.eng), ("Payment Pending", self.eng),
            ("Completed", self.eng), ("Completed", self.eng2), ("Rejected", self.eng),
        ):
            self.db.add(InstallationRequest(
                customer_name="C", contact_number="9999999999", status=status_, source="vendor",
                assigned_engineer=engineer.id if engineer else None,
            ))
        self.db.commit()

        def override():
            s = self.Session()
            try:
                yield s
            finally:
                s.close()

        app.dependency_overrides[get_db] = override
        self.client = TestClient(app)

    def tearDown(self):
        app.dependency_overrides.clear()
        self.db.close()

    def _user(self, email, role):
        u = User(name=email.split("@")[0], email=email, password_hash=hash_password("pw123456"), role=role, is_active=True)
        self.db.add(u)
        self.db.flush()
        return u

    def h(self, user):
        return {"Authorization": f"Bearer {create_access_token(subject=str(user.id), extra_claims={'role': user.role})}"}

    def test_every_status_belongs_to_exactly_one_stage(self):
        from app.routers.installations import STATUSES

        missing = [s for s in STATUSES if s not in STAGE_OF]
        self.assertEqual(missing, [], "a status with no stage would vanish from the stage chips")
        self.assertEqual(len(STAGE_OF), sum(len(statuses) for _k, _l, statuses in STAGES), "no status in two stages")
        self.assertEqual(stage_counts({"Assigned": 2, "Completed": 1})["as"], 2)

    def test_the_list_counts_every_stage_and_filters_by_one(self):
        r = self.client.get("/api/installations", headers=self.h(self.admin))
        self.assertEqual(r.status_code, 200, r.text)
        body = r.json()
        self.assertEqual(body["stage_counts"], {"na": 2, "as": 2, "ip": 1, "vp": 1, "ap": 0, "in": 1, "pay": 1, "done": 2, "rr": 1})
        self.assertEqual(body["total"], 11)
        for key, want in (("na", 2), ("as", 2), ("ip", 1), ("vp", 1), ("in", 1), ("pay", 1), ("done", 2), ("rr", 1)):
            got = self.client.get("/api/installations", params={"stage": key}, headers=self.h(self.admin)).json()
            self.assertEqual(got["total"], want, key)
            self.assertEqual(got["stage_counts"], body["stage_counts"], "the chips keep their counts while one is picked")

    def test_the_stage_works_with_the_status_and_search_filters(self):
        r = self.client.get("/api/installations", params={"stage": "ip", "status": "In Progress"}, headers=self.h(self.admin)).json()
        self.assertEqual([i["status"] for i in r["items"]], ["In Progress"])
        self.assertEqual(r["stage_counts"]["ip"], 1, "counts follow the other filters")

    def test_each_group_row_carries_its_own_stage_counts(self):
        items = self.client.get("/api/installations", headers=self.h(self.admin)).json()["items"]
        self.assertEqual(items[0]["group_stage_counts"], {"na": 2, "as": 2, "ip": 1, "vp": 1, "ap": 0, "in": 1, "pay": 1, "done": 2, "rr": 1})

    def test_gem_search_covers_both_order_links_counts_pagination_and_visibility(self):
        order = Order(order_no="GEMC-511687782817215", order_date=date.today())
        self.db.add(order)
        self.db.flush()
        item = OrderItem(order_id=order.id, item_code="SEARCH-ITEM")
        self.db.add(item)
        self.db.flush()
        direct = InstallationRequest(customer_name="Search buyer", contact_number="1234567890",
                                     source="vendor", order_id=order.id, status="Assigned", assigned_engineer=self.eng.id)
        legacy = InstallationRequest(customer_name="Other buyer", contact_number="2345678901",
                                     source="vendor", order_item_id=item.id, status="Completed", assigned_engineer=self.eng2.id)
        self.db.add_all([direct, legacy])
        self.db.commit()
        for term in ("gemc-511687782817215", "  7782817  "):
            response = self.client.get("/api/installations", params={"search": term}, headers=self.h(self.admin))
            self.assertEqual(response.status_code, 200, response.text)
            body = response.json()
            self.assertEqual({row["id"] for row in body["items"]}, {direct.id, legacy.id})
            self.assertEqual(body["total"], 2)
            self.assertEqual(body["stage_counts"]["as"], 1)
            self.assertEqual(body["stage_counts"]["done"], 1)
        page = self.client.get("/api/installations", params={"search": "7782817", "per_page": 1}, headers=self.h(self.admin)).json()
        self.assertEqual(page["total"], 2)
        self.assertEqual(len(page["items"]), 1)
        staged = self.client.get("/api/installations", params={"search": "7782817", "stage": "done"}, headers=self.h(self.admin)).json()
        self.assertEqual([row["id"] for row in staged["items"]], [legacy.id])
        self.assertEqual(staged["stage_counts"]["as"], 1)
        mine = self.client.get("/api/installations", params={"search": "7782817"}, headers=self.h(self.eng)).json()
        self.assertEqual([row["id"] for row in mine["items"]], [direct.id])
        missing = self.client.get("/api/installations", params={"search": "GEMC-NOT-FOUND"}, headers=self.h(self.admin)).json()
        self.assertEqual(missing["total"], 0)

    def test_search_keeps_customer_mobile_product_and_treats_wildcards_literally(self):
        self.db.add(InstallationRequest(customer_name="Buyer_100%", contact_number="9876543210",
                                        product_name="Unique cooler", source="vendor", status="Pending"))
        self.db.commit()
        for term in ("buyer_100%", "987654", "unique cooler", "_", "%"):
            response = self.client.get("/api/installations", params={"search": term}, headers=self.h(self.admin))
            self.assertEqual(response.status_code, 200, response.text)
            self.assertEqual(response.json()["total"], 1, term)

    def test_an_engineer_sees_only_the_stages_of_his_own_requests(self):
        r = self.client.get("/api/installations", headers=self.h(self.eng2)).json()
        self.assertEqual(r["stage_counts"], {"na": 0, "as": 1, "ip": 0, "vp": 0, "ap": 0, "in": 0, "pay": 0, "done": 1, "rr": 0})

    def test_the_dashboard_summary_has_the_stages_too(self):
        r = self.client.get("/api/dashboard/installation-summary", headers=self.h(self.admin)).json()
        self.assertEqual(r["stages"], {"na": 2, "as": 2, "ip": 1, "vp": 1, "ap": 0, "in": 1, "pay": 1, "done": 2, "rr": 1})
        mine = self.client.get("/api/dashboard/installation-summary", headers=self.h(self.eng2)).json()
        self.assertEqual(mine["stages"]["as"], 1)
        self.assertEqual(mine["stages"]["na"], 0)


if __name__ == "__main__":
    unittest.main()
