from __future__ import annotations

import unittest

from parts_base import PartsTestBase


class ClaimPartyOnApprovalTests(PartsTestBase):
    """The Service Manager must say to whom a claim is given before passing the request on, and Admin sees it."""

    def _request(self):
        body = {"kind": "expense", "description": "Missing copper pipe", "amount": "400.00", "crm_service_request_id": 42, "crm_serial_no": "SER-1"}
        return self.post("/api/parts/requests", body, self.eng).json()["id"]

    def _claim(self, rid, **kw):
        from app.models.shortage_claim import ShortageClaim

        c = ShortageClaim(claim_no="SHC-00001", flow="parts", item_request_id=rid, description="pipe short", raised_by_user_id=self.eng.id, stage="svm", **kw)
        self.db.add(c)
        self.db.commit()
        return c

    def test_cannot_pass_it_on_until_the_claim_has_a_party(self):
        rid = self._request()
        self._claim(rid)
        r = self.post(f"/api/parts/requests/{rid}/approve", {}, self.svm)
        self.assertEqual(r.status_code, 409, r.text)
        self.assertIn("Say to whom the claim is given", r.json()["detail"])
        self.assertIn("SHC-00001", r.json()["detail"])
        self.assertEqual(self.get(f"/api/parts/requests/{rid}", self.svm).json()["stage"], "svm", "nothing moved")

    def test_with_a_party_it_goes_on_and_admin_sees_who_gave_it(self):
        from app.models.shortage_claim import ShortageClaimEvent

        rid = self._request()
        c = self._claim(rid, responsible_type="company")
        self.db.add(ShortageClaimEvent(claim_id=c.id, kind="decided", text="pinned on Company", by_user_id=self.svm.id))
        self.db.commit()
        r = self.post(f"/api/parts/requests/{rid}/approve", {}, self.svm)
        self.assertEqual((r.status_code, r.json()["stage"]), (200, "sub"), r.text)
        texts = [e["text"] for e in self.get(f"/api/parts/requests/{rid}", self.admin).json()["timeline"]]
        self.assertTrue(any(t.startswith("Claim SHC-00001 is on Company (given by ") and self.svm.name in t for t in texts), texts)

    def test_no_claim_no_new_rule(self):
        rid = self._request()
        self.assertEqual(self.post(f"/api/parts/requests/{rid}/approve", {}, self.svm).status_code, 200)

    def test_admin_stage_is_not_blocked(self):
        rid = self._request()
        self.post(f"/api/parts/requests/{rid}/approve", {}, self.svm)
        self._claim(rid)
        self.assertEqual(self.post(f"/api/parts/requests/{rid}/approve", {}, self.admin).status_code, 200)


if __name__ == "__main__":
    unittest.main()
