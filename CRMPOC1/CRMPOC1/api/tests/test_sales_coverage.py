from __future__ import annotations

import unittest

from sales_base import SalesTestBase


class CoverageTests(SalesTestBase):
    def cover(self, who, coverage, **extra):
        return self.put(f"/api/sales/team/{who.id}/profile", {"coverage": coverage, **extra}, self.admin)

    def owner_of(self, **lead):
        out = self.new_lead(types="retail", lead_type="retail", **lead)
        return out["owner_name"]

    def test_all_india_state_district_and_pin_code_coverage(self):
        # Pooja has no retail, so give both retail; Amit covers only Delhi (whole) and two districts of UP, Pooja all India
        self.put(f"/api/sales/team/{self.pooja.id}/profile", {"types_handled": "retail"}, self.admin)
        self.assertEqual(self.cover(self.amit, {"mode": "states", "states": {
            "Delhi": {"all": True},
            "Uttar Pradesh": {"all": False, "districts": ["Ghaziabad", "Gautam Buddha Nagar"], "pins": ["226001"]},
        }}).status_code, 200)
        self.assertEqual(self.cover(self.pooja, {"mode": "all"}).status_code, 200)
        # a named place wins over All India
        self.assertEqual(self.owner_of(state="Delhi", phone="98000 10001"), "Amit Verma")
        self.assertEqual(self.owner_of(state="Uttar Pradesh", district="Ghaziabad", phone="98000 10002"), "Amit Verma")
        # a district Amit does not cover, but a pin code he added, still comes to him
        self.assertEqual(self.owner_of(state="Uttar Pradesh", district="Lucknow", pincode="226001", phone="98000 10003"), "Amit Verma")
        # a district Amit does not cover goes to the All India person
        self.assertEqual(self.owner_of(state="Uttar Pradesh", district="Varanasi", phone="98000 10004"), "Pooja Singh")
        # spelling and capitals of the district do not matter
        self.assertEqual(self.owner_of(state="uttar pradesh", district="GAUTAM BUDDHA  NAGAR", phone="98000 10005"), "Amit Verma")

    def test_the_profile_keeps_what_was_saved_and_checks_it(self):
        r = self.cover(self.amit, {"mode": "states", "states": {"Haryana": {"all": False, "districts": ["Gurugram"], "pins": ["122001"]}}})
        self.assertEqual(r.json()["coverage"]["states"]["Haryana"]["districts"], ["Gurugram"])
        self.assertEqual(self.cover(self.amit, {"mode": "states", "states": {"Haryana": {"all": False, "districts": [], "pins": ["12200"]}}}).status_code, 400)
        self.assertEqual(self.cover(self.amit, {"mode": "states", "states": {"Haryana": {"all": False}}}).status_code, 400)
        self.assertEqual(self.cover(self.amit, {"mode": "nowhere"}).status_code, 400)
        # only the manager side (types_edit) changes coverage
        r = self.put(f"/api/sales/team/{self.amit.id}/profile", {"coverage": {"mode": "all"}}, self.amit)
        self.assertEqual(r.status_code, 403)

    def test_a_profile_without_coverage_still_works_from_the_older_areas_list(self):
        self.put(f"/api/sales/team/{self.pooja.id}/profile", {"types_handled": "retail"}, self.admin)
        self.assertEqual(self.owner_of(state="Delhi", phone="98000 10006"), "Amit Verma")  # areas: Uttar Pradesh, Delhi


if __name__ == "__main__":
    unittest.main()
