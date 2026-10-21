from __future__ import annotations

import unittest

from sales_base import SalesTestBase


class PartnerEnquiryTests(SalesTestBase):
    """A website visitor who chooses "Partner" must reach the Sales Manager, like a partner registration form."""

    def setUp(self):
        super().setUp()
        from app.sales import leads as L

        L.set_setting(self.sdb, "auto_assign_new", "0")  # the Sales Manager gives it, as in real life
        self.sdb.commit()
        self.sync()  # first run: start from now

    def leads(self):
        return self.get("/api/sales/leads", self.karan).json()["items"]

    def test_a_partner_enquiry_from_the_website_becomes_a_dealer_lead_for_the_sales_manager(self):
        c = self.complaint("IDC_P1", "LS Trading Corporation", "78896 61218", "Gem's Partner", qtype="Partner")
        c.remark = "Gst No: 01PLFPS2346Q1ZE"
        c.source = "website"
        self.db.commit()
        stats = self.sync()
        self.assertEqual(stats["complaints"], 1)
        rows = self.leads()
        self.assertEqual(len(rows), 1)
        lead = rows[0]
        self.assertEqual((lead["crm_ref"], lead["crm_kind"], lead["lead_type"]), ("IDC_P1", "complaint", "dealer"))
        self.assertEqual(lead["item"], "Wants to become a partner")
        self.assertIsNone(lead["owner_name"], "unassigned: the Sales Manager gives it to the team")
        self.assertIn("01PLFPS2346Q1ZE", lead.get("details") or "")
        self.assertEqual(self.sync()["complaints"], 0, "not doubled")

    def test_the_manager_can_give_it_to_the_sales_team(self):
        self.complaint("IDC_P2", "M.c.enterprises", "98765 00011", "Partner", qtype="Partner")
        self.sync()
        lead = self.leads()[0]
        r = self.post(f"/api/sales/leads/{lead['id']}/give", {"owner_user_id": self.amit.id}, self.karan)
        self.assertEqual(r.status_code, 200, r.text)
        self.assertEqual(self.leads()[0]["owner_name"], "Amit Verma")

    def test_type_is_read_without_caring_about_capitals_or_spaces_and_other_types_stay_out(self):
        self.complaint("IDC_P3", "Spaced Out", "90000 11111", "wants to join", qtype=" partner ")
        self.complaint("IDC_O1", "Someone", "90000 22222", "general question", qtype="Others")
        self.complaint("IDC_S1", "Service Customer", "90000 33333", "AC not cooling", qtype="Service")
        self.complaint("IDC_I1", "Install Customer", "90000 44444", "install my AC", qtype="Installation")
        stats = self.sync()
        self.assertEqual(stats["complaints"], 1)
        self.assertEqual([r["crm_ref"] for r in self.leads()], ["IDC_P3"])

    def test_sales_enquiries_still_work_and_backfill_brings_in_older_partner_enquiries(self):
        self.complaint("IDC_S2", "Gupta Electricals", "98111 22334", "I need 20 split ACs. Please send the price.", qtype="Sales")
        self.complaint("IDC_P4", "Old Partner", "90000 55555", "Partner", qtype="Partner")
        self.assertEqual(self.sync()["complaints"], 2)
        self.complaint("IDC_P5", "Another", "90000 66666", "Partner", qtype="Partner")
        self.sync()
        self.assertEqual(len(self.leads()), 3)
        # an enquiry the sync never saw is brought in on request, once
        stats = self.sync(backfill_days=30)
        self.assertEqual(stats["complaints"], 0, "nothing missing, nothing doubled")


if __name__ == "__main__":
    unittest.main()
