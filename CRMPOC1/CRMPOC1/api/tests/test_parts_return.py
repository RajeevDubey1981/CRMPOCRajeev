from __future__ import annotations

import unittest

from parts_base import PartsTestBase


class ReturnToServiceManagerTests(PartsTestBase):
    """Admin and Sub Admin can approve, reject, or send a request back to the Service Manager."""

    def _waiting_for_admin(self, amount="5000.00"):
        body = {"kind": "part", "description": "Inverter compressor x 1", "crm_service_request_id": 42, "crm_item_code": "8901234500011", "amount": amount}
        r = self.post("/api/parts/requests", body, self.eng)
        self.assertEqual(r.status_code, 201, r.text)
        req = r.json()
        # the photos the kind needs
        from app.parts import service as svc
        from app.parts.models import ItemRequest

        row = self.pdb.get(ItemRequest, req["id"])
        row.required_photos_override = 0
        self.pdb.commit()
        r = self.post(f"/api/parts/requests/{req['id']}/approve", {}, self.svm)
        self.assertEqual(r.status_code, 200, r.text)
        self.assertEqual(r.json()["stage"], "sub")
        return req["id"]

    def test_the_buttons_each_role_gets_at_the_admin_stage(self):
        rid = self._waiting_for_admin()
        sub = self.get(f"/api/parts/requests/{rid}", self.sub).json()
        self.assertTrue(sub["can_act"] and sub["can_return"], "Sub Admin: approve, reject and return")
        admin = self.get(f"/api/parts/requests/{rid}", self.admin).json()
        self.assertTrue(admin["can_act"] and admin["can_return"])
        svm = self.get(f"/api/parts/requests/{rid}", self.svm).json()
        self.assertFalse(svm["can_act"] or svm["can_return"], "the Service Manager has done their part")

    def test_returning_sends_it_back_to_the_service_manager_with_the_reason(self):
        rid = self._waiting_for_admin()
        r = self.post(f"/api/parts/requests/{rid}/return", {"reason": "Please check the price with the supplier"}, self.sub)
        self.assertEqual(r.status_code, 200, r.text)
        d = r.json()
        self.assertEqual(d["stage"], "svm")
        self.assertFalse(d["can_return"])
        timeline = self.get(f"/api/parts/requests/{rid}", self.sub).json()["timeline"]
        self.assertIn("Returned to the Service Manager by Sub Admin: Please check the price with the supplier", timeline[-1]["text"])
        # the Service Manager sees it as theirs again and the chain starts over
        self.assertTrue(self.get(f"/api/parts/requests/{rid}", self.svm).json()["can_act"])
        self.assertEqual(self.post(f"/api/parts/requests/{rid}/approve", {}, self.svm).json()["stage"], "sub")
        self.assertEqual(self.post(f"/api/parts/requests/{rid}/approve", {}, self.admin).json()["stage"], "done")

    def test_reject_still_works_after_a_return(self):
        rid = self._waiting_for_admin()
        self.post(f"/api/parts/requests/{rid}/return", {"reason": "Check the amount"}, self.admin)
        self.post(f"/api/parts/requests/{rid}/approve", {}, self.svm)
        r = self.post(f"/api/parts/requests/{rid}/reject", {"reason": "Not covered"}, self.sub)
        self.assertEqual((r.status_code, r.json()["stage"]), (200, "rejected"))

    def test_only_admin_and_sub_admin_can_return_and_only_from_their_stage(self):
        rid = self._waiting_for_admin()
        for who in (self.svm, self.eng, self.sales):
            self.assertIn(self.post(f"/api/parts/requests/{rid}/return", {"reason": "no"}, who).status_code, (403, 404), who.role)
        self.assertEqual(self.get(f"/api/parts/requests/{rid}", self.sub).json()["stage"], "sub", "nothing changed")
        # a request that is still with the Service Manager, or already decided, cannot be returned
        body = {"kind": "expense", "description": "Taxi to site", "amount": "400.00"}
        fresh = self.post("/api/parts/requests", body, self.eng).json()["id"]
        self.assertEqual(self.post(f"/api/parts/requests/{fresh}/return", {"reason": "no"}, self.sub).status_code, 409)
        self.post(f"/api/parts/requests/{rid}/approve", {}, self.admin)
        self.assertEqual(self.post(f"/api/parts/requests/{rid}/return", {"reason": "too late"}, self.sub).status_code, 409)

    def test_a_reason_is_required(self):
        rid = self._waiting_for_admin()
        self.assertEqual(self.post(f"/api/parts/requests/{rid}/return", {"reason": ""}, self.sub).status_code, 422)
        self.assertEqual(self.post(f"/api/parts/requests/{rid}/return", {}, self.sub).status_code, 422)


if __name__ == "__main__":
    unittest.main()
