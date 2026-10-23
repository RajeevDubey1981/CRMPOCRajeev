"""Missing-item claims: raising one from the field, the mandatory-photo gate, deciding who's responsible
(manufacturer / transporter / insurance), the two-stage approval chain, rejection, and role access."""
from __future__ import annotations

import unittest

import test_queries as _q

from app.models import Courier, Vendor


class ShortageClaimTests(unittest.TestCase):
    setUp = _q.QueriesTests.setUp
    tearDown = _q.QueriesTests.tearDown
    _user = _q.QueriesTests._user
    h = _q.QueriesTests.h

    def setUp(self):  # noqa: F811
        _q.QueriesTests.setUp(self)
        self.vendor_row = Vendor(vendor_code="V-1", name_of_firm="Shree Cooling Industries")
        self.courier_row = Courier(courier_name="Safexpress Logistics")
        self.db.add_all([self.vendor_row, self.courier_row])
        self.db.commit()

    def get(self, url, who, **kw):
        return self.client.get(url, headers=self.h(who), **kw)

    def post(self, url, body, who):
        return self.client.post(url, json=body, headers=self.h(who))

    def _raise(self, who, **kw):
        body = {"flow": "installation", "description": "Unit arrived without the copper pipe set.", "items": ["Copper pipe"], **kw}
        r = self.post("/api/shortage-claims", body, who)
        self.assertEqual(r.status_code, 201, r.text)
        return r.json()

    def test_engineer_raises_a_claim_and_it_needs_photos_before_approval(self):
        claim = self._raise(self.eng)
        self.assertEqual(claim["stage"], "svm")
        self.assertEqual(claim["items"], ["Copper pipe"])

        detail = self.get(f"/api/shortage-claims/{claim['id']}", self.tech).json()
        self.assertEqual(len(detail["timeline"]), 1)
        self.assertEqual(detail["timeline"][0]["kind"], "raised")

        r = self.post(f"/api/shortage-claims/{claim['id']}/approve", {}, self.tech)
        self.assertEqual(r.status_code, 400, r.text)
        self.assertIn("photos", r.json()["detail"])

    def _add_photos(self, claim_id, who):
        for label in ("a", "b", "c", "d"):
            up = self.client.post(
                f"/api/shortage-claims/{claim_id}/photos",
                files={"photo": (f"{label}.jpg", b"\xff\xd8\xff" + b"0" * 20, "image/jpeg")},
                data={"label": label},
                headers=self.h(who),
            )
            self.assertEqual(up.status_code, 201, up.text)

    def test_cannot_approve_before_responsibility_is_decided(self):
        claim = self._raise(self.eng)
        self._add_photos(claim["id"], self.eng)
        r = self.post(f"/api/shortage-claims/{claim['id']}/approve", {}, self.tech)
        self.assertEqual(r.status_code, 400, r.text)
        self.assertIn("responsible", r.json()["detail"])

    def test_full_chain_pinned_on_manufacturer_needs_both_stages(self):
        claim = self._raise(self.eng)
        self._add_photos(claim["id"], self.eng)

        r = self.post(f"/api/shortage-claims/{claim['id']}/decide", {"responsible_type": "mfg", "vendor_id": self.vendor_row.id}, self.tech)
        self.assertEqual(r.status_code, 200, r.text)
        self.assertEqual(r.json()["party_name"], "Shree Cooling Industries")

        r2 = self.post(f"/api/shortage-claims/{claim['id']}/approve", {}, self.tech)
        self.assertEqual(r2.status_code, 200, r2.text)
        self.assertEqual(r2.json()["stage"], "sub")

        # service manager can no longer act once it's with Admin/Sub Admin
        r3 = self.post(f"/api/shortage-claims/{claim['id']}/approve", {}, self.tech)
        self.assertEqual(r3.status_code, 403)

        r4 = self.post(f"/api/shortage-claims/{claim['id']}/approve", {}, self.sub)
        self.assertEqual(r4.status_code, 200, r4.text)
        self.assertEqual(r4.json()["stage"], "done")

    def test_pinned_on_transporter_and_insurance(self):
        c1 = self._raise(self.eng, items=["Stabilizer"])
        self._add_photos(c1["id"], self.eng)
        r = self.post(f"/api/shortage-claims/{c1['id']}/decide", {"responsible_type": "trans", "courier_id": self.courier_row.id}, self.tech)
        self.assertEqual(r.json()["party_name"], "Safexpress Logistics")

        c2 = self._raise(self.eng, items=["Gas charge"])
        self._add_photos(c2["id"], self.eng)
        r2 = self.post(f"/api/shortage-claims/{c2['id']}/decide", {"responsible_type": "ins", "insurer_name": "HDFC Ergo — Transit Policy TP-88213"}, self.tech)
        self.assertEqual(r2.json()["party_name"], "HDFC Ergo — Transit Policy TP-88213")

    def test_rejection_logs_a_reason(self):
        claim = self._raise(self.eng)
        r = self.post(f"/api/shortage-claims/{claim['id']}/reject", {"reason": "Item was delivered separately, confirmed with customer"}, self.tech)
        self.assertEqual(r.status_code, 200, r.text)
        self.assertEqual(r.json()["stage"], "rejected")
        detail = self.get(f"/api/shortage-claims/{claim['id']}", self.tech).json()
        self.assertIn("delivered separately", detail["timeline"][-1]["text"])

    def test_engineer_cannot_approve_or_decide(self):
        # engineers have no "claims" view permission by default (seed.py), so they get a plain 404 here,
        # same as the existing customer-claims module does for anyone without view rights.
        claim = self._raise(self.eng)
        self._add_photos(claim["id"], self.eng)
        r = self.post(f"/api/shortage-claims/{claim['id']}/decide", {"responsible_type": "mfg", "vendor_id": self.vendor_row.id}, self.eng)
        self.assertEqual(r.status_code, 404)
        r2 = self.post(f"/api/shortage-claims/{claim['id']}/approve", {}, self.eng)
        self.assertEqual(r2.status_code, 404)

    def test_vendor_role_has_no_access_to_the_claims_list(self):
        self._raise(self.eng)
        r = self.get("/api/shortage-claims", self.vendor)
        self.assertEqual(r.status_code, 200)
        self.assertEqual(r.json(), [])

    def test_filters_and_export(self):
        self._raise(self.eng, items=["Copper pipe"])
        self._raise(self.eng, items=["Remote control"])
        rows = self.get("/api/shortage-claims?item=Remote control", self.tech).json()
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]["items"], ["Remote control"])

        r = self.get("/api/shortage-claims/export", self.tech)
        self.assertEqual(r.status_code, 200, r.text)
        self.assertIn("Claim No", r.text)

    def test_parties_endpoint_lists_vendors_and_couriers(self):
        r = self.get("/api/shortage-claims/parties", self.tech)
        self.assertEqual(r.status_code, 200, r.text)
        self.assertIn("Shree Cooling Industries", [v["name"] for v in r.json()["vendors"]])
        self.assertIn("Safexpress Logistics", [c["name"] for c in r.json()["couriers"]])
