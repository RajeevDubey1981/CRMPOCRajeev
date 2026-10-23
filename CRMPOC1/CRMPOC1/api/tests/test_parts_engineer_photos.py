from __future__ import annotations

import unittest
from decimal import Decimal

from parts_base import PartsTestBase


class EngineerPhotosOnApprovalTests(PartsTestBase):
    """A part request raised from the engineer's observation carries no photos of its own; the approver must still see the
    engineer's pictures of that unit, whoever opens it."""

    def _field_photo(self, serial, path):
        from app.models.field_photo import FieldPhoto

        self.db.add(FieldPhoto(source="service_unit", serial_no=serial, file_path=path, latitude=Decimal("28.6139000"), longitude=Decimal("77.2090000"), uploaded_by_user_id=self.eng.id))
        self.db.commit()

    def _request(self, serial="SER-9"):
        body = {"kind": "part", "description": "Compressor", "crm_service_request_id": 42, "crm_serial_no": serial, "amount": "5000.00"}
        rid = self.post("/api/parts/requests", body, self.eng).json()["id"]
        from app.parts.models import ItemRequest

        self.pdb.get(ItemRequest, rid).required_photos_override = 0
        self.pdb.commit()
        return rid

    def test_admin_and_sub_admin_see_the_engineers_photos_of_that_unit(self):
        self._field_photo("SER-9", "/uploads/field_photos/a.jpg")
        self._field_photo("SER-9", r"C:\srv\uploads\field_photos\b.jpg")
        self._field_photo("OTHER", "/uploads/field_photos/c.jpg")
        rid = self._request()
        for who in (self.admin, self.sub, self.svm):
            d = self.get(f"/api/parts/requests/{rid}", who).json()
            self.assertEqual([p["file_path"] for p in d["engineer_photos"]], ["/uploads/field_photos/a.jpg", "/uploads/field_photos/b.jpg"], who.role)
            self.assertEqual(d["engineer_photos"][0]["uploaded_by_name"], self.eng.name)
            self.assertIn("google.com/maps", d["engineer_photos"][0]["map_url"])

    def test_no_photos_gives_an_empty_list(self):
        self.assertEqual(self.get(f"/api/parts/requests/{self._request()}", self.admin).json()["engineer_photos"], [])


if __name__ == "__main__":
    unittest.main()
