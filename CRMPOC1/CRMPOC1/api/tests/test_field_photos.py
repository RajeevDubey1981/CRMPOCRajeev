from __future__ import annotations

import os
import sys
import tempfile
import unittest
from datetime import date
from pathlib import Path

os.environ.setdefault("MYSQL_DATABASE_URL", "sqlite://")
os.environ.setdefault("UPLOAD_DIR", str(Path(tempfile.mkdtemp(prefix="indcool_t_")) / "uploads"))
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from fastapi.testclient import TestClient
from sqlalchemy import create_engine, select
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.database import Base, get_db
from app.main import app
from app.models import FieldPhoto, Order, OrderItem, ServiceRequest, ServiceRequestItem, ServiceRequestUnit, User
from app.models.installation import InstallationEngineerSerial, InstallationRequest
from app.security import create_access_token, hash_password
from app.seed import seed_roles

JPEG = b"\xff\xd8\xff\xe0" + b"\x00" * 200
PNG = b"\x89PNG\r\n\x1a\n" + b"\x00" * 200


class FieldPhotoTests(unittest.TestCase):
    def setUp(self):
        engine = create_engine("sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool)
        Base.metadata.create_all(engine)
        self.Session = sessionmaker(bind=engine, autoflush=False, autocommit=False, future=True)
        self.db = self.Session()
        seed_roles(self.db)

        def override():
            s = self.Session()
            try:
                yield s
            finally:
                s.close()

        app.dependency_overrides[get_db] = override
        self.client = TestClient(app)
        self.admin = self._user("admin@t.com", "admin")
        self.eng1 = self._user("e1@t.com", "engineer")
        self.eng2 = self._user("e2@t.com", "engineer")
        order = Order(order_no="ORD-1", order_date=date.today())
        self.db.add(order)
        self.db.flush()
        oi = OrderItem(order_id=order.id)
        self.db.add(oi)
        self.db.flush()
        sr = ServiceRequest(request_no="SR-1", customer_name="C", customer_mobile="9999999999", assigned_engineer_id=self.eng1.id)
        self.db.add(sr)
        self.db.flush()
        item = ServiceRequestItem(service_request_id=sr.id, order_id=order.id, item_code="X1")
        self.db.add(item)
        self.db.flush()
        self.unit = ServiceRequestUnit(service_request_id=sr.id, service_request_item_id=item.id, order_item_id=oi.id,
                                       serial_no="SER-001", assigned_engineer_id=self.eng1.id)
        self.db.add(self.unit)
        inst = InstallationRequest(customer_name="C", contact_number="9999999999", assigned_engineer=self.eng1.id, source="vendor")
        self.db.add(inst)
        self.db.flush()
        self.iserial = InstallationEngineerSerial(installation_request_id=inst.id, serial_no="INS-001")
        self.db.add(self.iserial)
        self.db.commit()

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

    def post(self, path, user, *, lat="28.6139", lng="77.2090", acc="12.5", data=JPEG, name="m.jpg", mime="image/jpeg"):
        form = {"latitude": lat, "longitude": lng}
        if acc is not None:
            form["accuracy"] = acc
        form["captured_at"] = "2026-10-05T10:15:00Z"
        return self.client.post(path, data=form, files={"photo": (name, data, mime)}, headers=self.h(user))

    def test_engineer_adds_photo_with_location_and_admin_sees_it(self):
        path = f"/api/field-photos/service-units/{self.unit.id}"
        r = self.post(path, self.eng1)
        self.assertEqual(r.status_code, 201, r.text)
        out = r.json()
        self.assertEqual((out["latitude"], out["longitude"], out["accuracy_m"]), (28.6139, 77.209, 12.5))
        self.assertEqual(out["serial_no"], "SER-001")
        self.assertTrue(out["file_path"].startswith("/uploads/field_photos/"))
        self.assertIn("maps?q=28.6139000,77.2090000", out["map_url"])
        self.assertEqual(out["uploaded_by_name"], "e1")
        seen = self.client.get(path, headers=self.h(self.admin))
        self.assertEqual(seen.status_code, 200)
        self.assertEqual(len(seen.json()), 1)
        self.assertEqual(len(self.client.get(path, headers=self.h(self.eng1)).json()), 1)

    def test_installation_serial_photo(self):
        path = f"/api/field-photos/installation-serials/{self.iserial.id}"
        r = self.post(path, self.eng1, data=PNG, name="m.png", mime="image/png")
        self.assertEqual(r.status_code, 201, r.text)
        self.assertEqual(r.json()["serial_no"], "INS-001")
        self.assertEqual(len(self.client.get(path, headers=self.h(self.admin)).json()), 1)

    def test_location_is_required_and_must_be_real(self):
        path = f"/api/field-photos/service-units/{self.unit.id}"
        r = self.client.post(path, data={}, files={"photo": ("m.jpg", JPEG, "image/jpeg")}, headers=self.h(self.eng1))
        self.assertEqual(r.status_code, 422)
        self.assertEqual(self.post(path, self.eng1, lat="0", lng="0").status_code, 400)
        self.assertEqual(self.post(path, self.eng1, lat="95", lng="77").status_code, 400)
        self.assertEqual(self.post(path, self.eng1, lat="28", lng="190").status_code, 400)
        self.assertEqual(self.post(path, self.eng1, acc="-3").status_code, 400)
        self.assertEqual(self.db.scalars(select(FieldPhoto)).all(), [])

    def test_other_engineer_and_admin_cannot_add(self):
        path = f"/api/field-photos/service-units/{self.unit.id}"
        self.assertIn(self.post(path, self.eng2).status_code, (403, 404))
        self.assertEqual(self.post(path, self.admin).status_code, 403)
        ipath = f"/api/field-photos/installation-serials/{self.iserial.id}"
        self.assertIn(self.post(ipath, self.eng2).status_code, (403, 404))
        self.assertEqual(self.post(ipath, self.admin).status_code, 403)

    def test_other_engineer_cannot_look(self):
        path = f"/api/field-photos/service-units/{self.unit.id}"
        self.post(path, self.eng1)
        self.assertEqual(self.client.get(path, headers=self.h(self.eng2)).status_code, 404)
        self.assertEqual(self.client.get(path).status_code, 401)

    def test_only_pictures_and_a_limit_per_serial(self):
        path = f"/api/field-photos/service-units/{self.unit.id}"
        self.assertEqual(self.post(path, self.eng1, data=b"%PDF-1.4 x", name="a.pdf", mime="application/pdf").status_code, 400)
        self.assertEqual(self.post(path, self.eng1, data=b"not an image", name="a.jpg").status_code, 400)
        for _ in range(4):
            self.assertEqual(self.post(path, self.eng1).status_code, 201)
        self.assertEqual(self.post(path, self.eng1).status_code, 400)

    def test_engineer_cannot_verify_a_serial_without_a_photo(self):
        url = f"/api/services/{self.unit.service_request_id}/verify-serial"
        body = {"unit_id": self.unit.id, "serial_no": "SER-001"}
        r = self.client.post(url, json=body, headers=self.h(self.eng1))
        self.assertEqual(r.status_code, 400, r.text)
        self.assertIn("at least 1 photo", r.json()["detail"])
        self.assertIn("SER-001", r.json()["detail"])
        bulk = self.client.post(f"/api/services/{self.unit.service_request_id}/verify-serials-bulk", json={"unit_ids": [self.unit.id]}, headers=self.h(self.eng1))
        self.assertEqual(bulk.status_code, 400, bulk.text)
        self.assertEqual(self.post(f"/api/field-photos/service-units/{self.unit.id}", self.eng1).status_code, 201)
        ok = self.client.post(url, json=body, headers=self.h(self.eng1))
        self.assertEqual(ok.status_code, 200, ok.text)

    def test_missing_serial_is_404(self):
        self.assertEqual(self.post("/api/field-photos/service-units/9999", self.eng1).status_code, 404)
        self.assertEqual(self.client.get("/api/field-photos/installation-serials/9999", headers=self.h(self.admin)).status_code, 404)


if __name__ == "__main__":
    unittest.main()
