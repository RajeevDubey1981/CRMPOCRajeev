"""The Parts API: catalogue CRUD, raising a request, the mandatory-photo gate, the two-stage approval chain,
rejection, role access, and the discuss-link into Queries."""
from __future__ import annotations

from tests.parts_base import PartsTestBase


class CatalogueTests(PartsTestBase):
    def test_service_manager_can_add_a_part_with_fitments(self):
        r = self.post("/api/parts/catalogue", {"part_code": "SP-CMP-1501", "part_name": "Inverter compressor 1.5 T", "part_ean": "8909000100011", "price": "6800.00", "fits": ["8901234500011"]}, self.svm)
        self.assertEqual(r.status_code, 201, r.text)
        body = r.json()
        self.assertEqual(body["part_code"], "SP-CMP-1501")
        self.assertEqual(body["fits"], ["8901234500011"])

        listed = self.get("/api/parts/catalogue", self.svm).json()
        self.assertEqual(len(listed), 1)

    def test_engineer_cannot_add_a_part(self):
        r = self.post("/api/parts/catalogue", {"part_code": "SP-X", "part_name": "Door gasket"}, self.eng)
        self.assertEqual(r.status_code, 403)

    def test_duplicate_part_code_rejected(self):
        self.post("/api/parts/catalogue", {"part_code": "SP-1", "part_name": "Door gasket A"}, self.svm)
        r = self.post("/api/parts/catalogue", {"part_code": "SP-1", "part_name": "Door gasket B"}, self.svm)
        self.assertEqual(r.status_code, 409)

    def test_hidden_part_not_shown_to_engineer_or_sales(self):
        self.post("/api/parts/catalogue", {"part_code": "SP-2", "part_name": "Hidden one", "engineer_visible": False}, self.svm)
        self.assertEqual(self.get("/api/parts/catalogue", self.eng).json(), [])
        self.assertEqual(self.get("/api/parts/catalogue", self.sales).json(), [])
        self.assertEqual(len(self.get("/api/parts/catalogue", self.svm).json()), 1)


class RequestFlowTests(PartsTestBase):
    def _raise(self, who, **kw):
        body = {"kind": "part", "description": "Inverter compressor x 1", "crm_service_request_id": 42, "crm_item_code": "8901234500011", **kw}
        r = self.post("/api/parts/requests", body, who)
        self.assertEqual(r.status_code, 201, r.text)
        return r.json()

    def test_engineer_raises_a_part_request_under_threshold_closes_with_one_approval(self):
        req = self._raise(self.eng, amount="800.00")
        self.assertEqual(req["stage"], "svm")
        self.assertIsNone(req["amount"])  # engineers never see amounts

        detail = self.get(f"/api/parts/requests/{req['id']}", self.eng).json()
        self.assertEqual(len(detail["timeline"]), 1)
        self.assertEqual(detail["timeline"][0]["kind"], "raised")

        # cannot approve before 4 photos
        r = self.post(f"/api/parts/requests/{req['id']}/approve", {}, self.svm)
        self.assertEqual(r.status_code, 400, r.text)

        for label in ("Wide shot", "Close-up of damage", "Part's label-code", "With the unit-box"):
            up = self.client.post(
                f"/api/parts/requests/{req['id']}/photos",
                files={"photo": (f"{label}.jpg", b"\xff\xd8\xff" + b"0" * 20, "image/jpeg")},
                data={"label": label},
                headers=self.h(self.eng),
            )
            self.assertEqual(up.status_code, 201, up.text)

        r = self.post(f"/api/parts/requests/{req['id']}/approve", {}, self.svm)
        self.assertEqual(r.status_code, 200, r.text)
        self.assertEqual(r.json()["stage"], "done")  # under 1000: Service Manager alone closes it

    def test_part_over_threshold_needs_admin_too(self):
        req = self._raise(self.eng, amount="6800.00")
        for label in ("a", "b", "c", "d"):
            self.client.post(f"/api/parts/requests/{req['id']}/photos", files={"photo": (f"{label}.jpg", b"\xff\xd8\xff" + b"0" * 20, "image/jpeg")}, headers=self.h(self.eng))
        r = self.post(f"/api/parts/requests/{req['id']}/approve", {}, self.svm)
        self.assertEqual(r.json()["stage"], "sub")

        # a second Service Manager approval would be the wrong stage now
        r2 = self.post(f"/api/parts/requests/{req['id']}/approve", {}, self.svm)
        self.assertEqual(r2.status_code, 403)

        r3 = self.post(f"/api/parts/requests/{req['id']}/approve", {}, self.sub)
        self.assertEqual(r3.status_code, 200, r3.text)
        self.assertEqual(r3.json()["stage"], "done")

    def test_rejection_logs_a_reason_and_closes_it(self):
        req = self._raise(self.eng, amount="100.00")
        r = self.post(f"/api/parts/requests/{req['id']}/reject", {"reason": "Not covered under warranty"}, self.svm)
        self.assertEqual(r.status_code, 200, r.text)
        self.assertEqual(r.json()["stage"], "rejected")
        detail = self.get(f"/api/parts/requests/{req['id']}", self.svm).json()
        self.assertIn("Not covered under warranty", detail["timeline"][-1]["text"])

    def test_engineer_sees_only_their_own_requests(self):
        self._raise(self.eng, amount="100.00")
        other = self._user("eng2@t.com", "engineer", "Sunil Kumar")
        self.db.commit()
        body = {"kind": "part", "description": "Door gasket", "amount": "50.00"}
        self.post("/api/parts/requests", body, other)
        self.assertEqual(len(self.get("/api/parts/requests", self.eng).json()), 1)
        self.assertEqual(len(self.get("/api/parts/requests", self.svm).json()), 2)

    def test_sales_has_no_access_to_requests(self):
        req = self._raise(self.eng, amount="100.00")
        self.assertEqual(self.get("/api/parts/requests", self.sales).status_code, 404)
        self.assertEqual(self.get(f"/api/parts/requests/{req['id']}", self.sales).status_code, 404)

    def test_discuss_opens_a_linked_query_both_can_see(self):
        req = self._raise(self.eng, amount="6800.00")
        r = self.post(f"/api/parts/requests/{req['id']}/discuss", {"message": "Can you send a close-up of the label?"}, self.svm)
        self.assertEqual(r.status_code, 200, r.text)
        qid = r.json()["crm_query_id"]

        detail = self.get(f"/api/parts/requests/{req['id']}", self.svm).json()
        self.assertEqual(detail["crm_query_id"], qid)

        # both the engineer (owner) and the Service Manager (opener) can see the thread
        eng_view = self.get(f"/api/queries/{qid}", self.eng)
        svm_view = self.get(f"/api/queries/{qid}", self.svm)
        self.assertEqual(eng_view.status_code, 200, eng_view.text)
        self.assertEqual(svm_view.status_code, 200, svm_view.text)

        # cannot open a second discussion on the same request
        again = self.post(f"/api/parts/requests/{req['id']}/discuss", {"message": "another question"}, self.svm)
        self.assertEqual(again.status_code, 409)

    def test_supplied_only_after_approval_and_not_by_engineer(self):
        req = self._raise(self.eng, amount="100.00")
        r = self.post(f"/api/parts/requests/{req['id']}/supplied", {}, self.eng)
        self.assertEqual(r.status_code, 403)
        for label in ("a", "b", "c", "d"):
            self.client.post(f"/api/parts/requests/{req['id']}/photos", files={"photo": (f"{label}.jpg", b"\xff\xd8\xff" + b"0" * 20, "image/jpeg")}, headers=self.h(self.eng))
        self.post(f"/api/parts/requests/{req['id']}/approve", {}, self.svm)
        ok = self.post(f"/api/parts/requests/{req['id']}/supplied", {"note": "Handed over at the depot"}, self.svm)
        self.assertEqual(ok.status_code, 200, ok.text)
