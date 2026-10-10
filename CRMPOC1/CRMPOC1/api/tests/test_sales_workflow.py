from __future__ import annotations

import unittest
from datetime import date, timedelta

from sales_base import SalesTestBase


class WorkflowTests(SalesTestBase):
    def mine(self, **kw):
        """A lead that belongs to Amit."""
        lead = self.new_lead(state="Uttar Pradesh", **kw)
        self.assertEqual(lead["owner_name"], "Amit Verma")
        return lead

    def call(self, lead, outcome, who=None, **extra):
        r = self.post(f"/api/sales/leads/{lead['id']}/call", {"outcome": outcome, **extra}, who or self.amit)
        self.assertEqual(r.status_code, 200, r.text)
        return r.json()

    def test_a_new_lead_is_not_attended_until_its_owner_acts(self):
        lead = self.mine()
        self.assertEqual((lead["attended"], lead["attempts"], lead["status"]), (False, 0, "new"))
        counts = self.get("/api/sales/leads", self.karan).json()["counts"]
        self.assertEqual(counts["not_attended"], 1)
        self.assertEqual(len(self.get("/api/sales/leads?kpi=not_attended", self.karan).json()["items"]), 1)
        # the manager giving or looking at it does not mark it attended
        self.post(f"/api/sales/leads/{lead['id']}/priority", {"level": "high", "why": "Large order, key customer"}, self.karan)
        self.assertFalse(self.get(f"/api/sales/leads/{lead['id']}", self.karan).json()["attended"])
        out = self.call(lead, "Spoke: needs a quote", note="Wants 20 ACs", next_follow_up=(date.today() + timedelta(days=2)).isoformat())
        self.assertEqual((out["attended"], out["attempts"], out["status"]), (True, 1, "int"))
        self.assertIsNotNone(out["last_action_at"])
        self.assertEqual(self.get("/api/sales/leads", self.karan).json()["counts"]["not_attended"], 0)

    def test_no_answer_is_an_attempt_and_sets_tomorrow(self):
        lead = self.mine()
        out = self.call(lead, "No answer")
        self.assertEqual((out["attended"], out["attempts"], out["status"]), (True, 1, "con"))
        self.assertEqual(out["follow_up_on"], (date.today() + timedelta(days=1)).isoformat())
        out = self.call(lead, "Phone switched off")
        self.assertEqual(out["attempts"], 2)

    def test_a_call_moves_the_stage_forward_never_back(self):
        lead = self.mine()
        self.assertEqual(self.call(lead, "Sent a WhatsApp or mail")["status"], "con")
        self.assertEqual(self.call(lead, "Spoke: interested")["status"], "int")
        self.assertEqual(self.call(lead, "Spoke: will think and call back")["status"], "int")
        self.assertEqual(self.call(lead, "No answer")["status"], "int")

    def test_the_person_moves_the_stage_by_hand(self):
        lead = self.mine()
        r = self.post(f"/api/sales/leads/{lead['id']}/stage", {"stage": "neg", "note": "Customer asked for a better price"}, self.amit)
        self.assertEqual(r.status_code, 200, r.text)
        out = r.json()
        self.assertEqual((out["status"], out["attended"]), ("neg", True))
        self.assertTrue(self.get(f"/api/sales/leads/{lead['id']}", self.amit).json()["first_called"])
        detail = self.get(f"/api/sales/leads/{lead['id']}", self.amit).json()
        self.assertIn("New to Negotiation", [a["text"] for a in detail["activities"] if a["kind"] == "stage"][0])
        # a correction back is fine, the same stage and an unknown stage are not
        self.assertEqual(self.post(f"/api/sales/leads/{lead['id']}/stage", {"stage": "con"}, self.amit).json()["status"], "con")
        self.assertEqual(self.post(f"/api/sales/leads/{lead['id']}/stage", {"stage": "con"}, self.amit).status_code, 400)
        self.assertEqual(self.post(f"/api/sales/leads/{lead['id']}/stage", {"stage": "won"}, self.amit).status_code, 400)
        # someone else cannot move it
        self.assertEqual(self.post(f"/api/sales/leads/{lead['id']}/stage", {"stage": "int"}, self.pooja).status_code, 404)

    def test_closed_and_partner_leads_have_no_manual_stage(self):
        lead = self.mine()
        self.post(f"/api/sales/leads/{lead['id']}/dispose", {"reason": "noint", "note": "Not interested in the offer"}, self.amit)
        self.assertEqual(self.post(f"/api/sales/leads/{lead['id']}/stage", {"stage": "int"}, self.amit).status_code, 400)
        self.sync()
        reg = self.registration("PR-W-1")
        self.sync()
        partner = [x for x in self.get("/api/sales/leads", self.karan).json()["items"] if x["crm_kind"] == "partner"][0]
        self.assertEqual(self.post(f"/api/sales/leads/{partner['id']}/stage", {"stage": "int"}, self.karan).status_code, 400)

    def registration(self, no):
        from app.models import PartnerRegistration
        r = PartnerRegistration(registration_no=no, access_token=no + "-t", partner_type="Distributor", business_type="Partnership", name="Workflow Partner", mobile="99280 77777",
                                email="w@t.com", form_status="In Progress", onboarding_status="In Progress", state="Rajasthan", city="Jaipur")
        self.db.add(r)
        self.db.commit()
        return r

    def test_rating_and_a_quotation_also_count_as_attending(self):
        lead = self.mine()
        r = self.post(f"/api/sales/leads/{lead['id']}/rate", {"answers": {"quote": True}}, self.amit)
        self.assertTrue(r.json()["attended"])
        lead2 = self.mine(name="Second", phone="98000 33002")
        self.assertFalse(lead2["attended"])
        self.post(f"/api/sales/leads/{lead2['id']}/quotations", {"items": [{"item_name": "Fan", "qty": 1, "rate": 100}]}, self.amit)
        self.assertTrue(self.get(f"/api/sales/leads/{lead2['id']}", self.amit).json()["attended"])


if __name__ == "__main__":
    unittest.main()
