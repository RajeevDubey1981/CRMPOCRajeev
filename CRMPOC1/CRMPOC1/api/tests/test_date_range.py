from __future__ import annotations

import unittest
from datetime import date, datetime, timedelta, timezone

from sales_base import SalesTestBase

from app.services.date_range import day_in_range, utc_bounds


class DateRangeHelperTests(unittest.TestCase):
    def test_an_indian_day_runs_from_half_past_six_in_the_evening_utc_the_day_before(self):
        start, end = utc_bounds(date(2026, 10, 12), date(2026, 10, 12))
        self.assertEqual(start, datetime(2026, 10, 11, 18, 30))
        self.assertEqual(end, datetime(2026, 10, 12, 18, 30))
        self.assertEqual(utc_bounds(None, None), (None, None))
        self.assertEqual(utc_bounds(None, date(2026, 10, 12))[0], None)

    def test_a_late_evening_utc_time_belongs_to_the_next_indian_day(self):
        late = datetime(2026, 10, 11, 20, 0, tzinfo=timezone.utc)  # 1:30 am on 12 Oct in India
        self.assertTrue(day_in_range(late, date(2026, 10, 12), date(2026, 10, 12)))
        self.assertFalse(day_in_range(late, date(2026, 10, 11), date(2026, 10, 11)))
        self.assertTrue(day_in_range(late.replace(tzinfo=None), date(2026, 10, 12), None), "a time with no zone is read as UTC")
        self.assertFalse(day_in_range(None, date(2026, 10, 12), None))
        self.assertTrue(day_in_range(None, None, None))


class LeadDateFilterTests(SalesTestBase):
    def test_leads_and_the_tiles_follow_the_registered_dates(self):
        from app.sales.models import SalesLead

        old = self.new_lead(state="Uttar Pradesh", name="Old Lead", phone="9810000001")
        new = self.new_lead(state="Uttar Pradesh", name="New Lead", phone="9810000002")
        self.sdb.get(SalesLead, old["id"]).created_at = datetime.now(timezone.utc) - timedelta(days=20)
        self.sdb.commit()
        today = date.today().isoformat()
        week_ago = (date.today() - timedelta(days=7)).isoformat()

        everything = self.get("/api/sales/leads", self.karan).json()
        self.assertEqual(len(everything["items"]), 2)
        recent = self.get(f"/api/sales/leads?date_from={week_ago}&date_to={today}", self.karan).json()
        self.assertEqual([x["name"] for x in recent["items"]], ["New Lead"])
        self.assertEqual(recent["counts"]["all"], 1, "the tiles count only the chosen days")
        only_old = self.get(f"/api/sales/leads?date_to={week_ago}", self.karan).json()
        self.assertEqual([x["name"] for x in only_old["items"]], ["Old Lead"])
        self.assertIsNotNone(only_old["items"][0]["created_at"], "the Registered column has its time")
        nothing = self.get(f"/api/sales/leads?date_from={today}&date_to={today}&q=zzz", self.karan).json()
        self.assertEqual(nothing["items"], [])

    def test_a_team_member_still_sees_only_their_own_leads_inside_the_dates(self):
        mine = self.new_lead(state="Uttar Pradesh", name="Amit Lead", phone="9810000003")
        self.assertEqual(mine["owner_name"], "Amit Verma")
        today = date.today().isoformat()
        self.assertEqual(len(self.get(f"/api/sales/leads?date_from={today}", self.amit).json()["items"]), 1)
        self.assertEqual(len(self.get(f"/api/sales/leads?date_from={today}", self.pooja).json()["items"]), 0)

    def test_the_other_lists_accept_the_dates_and_count_the_complaint_tiles_by_them(self):
        today = date.today().isoformat()
        far = (date.today() - timedelta(days=400)).isoformat()
        for url in ("/api/orders", "/api/claims", "/api/partner-registrations", "/api/orders/export", "/api/claims/export", "/api/dashboard/complaints-summary"):
            r = self.get(f"{url}?date_from={far}&date_to={today}", self.admin)
            # an export may refuse this test user (no export permission), but never with 422: the dates are understood
            self.assertIn(r.status_code, (200, 403) if url.endswith("/export") else (200,), f"{url}: {r.text[:200]}")
        listed = self.get(f"/api/orders?date_from={today}&date_to={today}", self.admin).json()
        self.assertEqual(listed["total"], 0)
        self.assertEqual(self.get(f"/api/dashboard/complaints-summary?date_from={today}", self.admin).json()["pending"], 0)


if __name__ == "__main__":
    unittest.main()
