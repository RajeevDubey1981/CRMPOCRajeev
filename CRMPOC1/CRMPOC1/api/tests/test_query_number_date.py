from __future__ import annotations

import unittest
from datetime import datetime, timedelta, timezone

import test_queries as _q

from app.models.user_query import UserQuery
from app.services.date_range import IST


class QueryNumberDateTests(unittest.TestCase):
    # the same database, users and helpers as the Queries tests
    setUp = _q.QueriesTests.setUp
    tearDown = _q.QueriesTests.tearDown
    _user = _q.QueriesTests._user
    h = _q.QueriesTests.h
    raise_query = _q.QueriesTests.raise_query

    def search(self, text, who):
        r = self.client.get("/api/queries", params={"search": text}, headers=self.h(who))
        self.assertEqual(r.status_code, 200, r.text)
        return [row["subject"] for row in r.json()]

    def raised_at(self, qid, moment_utc):
        with self.Session() as s:
            q = s.get(UserQuery, qid)
            q.created_at = moment_utc
            s.commit()

    def test_every_query_gets_its_number_and_the_day_it_was_raised(self):
        a = self.raise_query(self.eng, subject="First")
        b = self.raise_query(self.vendor, subject="Second")
        self.assertEqual(a["query_no"], f"QRY-{a['id']:04d}")
        self.assertEqual(b["query_no"], f"QRY-{b['id']:04d}")
        self.assertNotEqual(a["query_no"], b["query_no"])
        self.assertEqual(a["raised_on"], datetime.now(IST).date().isoformat())
        row = self.client.get("/api/queries", headers=self.h(self.admin)).json()[0]
        self.assertTrue(row["query_no"].startswith("QRY-") and row["raised_on"])

    def test_nothing_is_typed_and_extra_values_are_ignored(self):
        r = self.client.post("/api/queries", json={"subject": "Help", "category": "Order", "message": "x", "query_no": "QRY-9999", "raised_on": "2001-01-01"}, headers=self.h(self.eng))
        self.assertEqual(r.status_code, 201, r.text)
        d = r.json()
        self.assertEqual(d["query_no"], f"QRY-{d['id']:04d}")
        self.assertEqual(d["raised_on"], datetime.now(IST).date().isoformat())

    def test_search_finds_a_query_by_its_number(self):
        a = self.raise_query(self.eng, subject="First")
        b = self.raise_query(self.eng2, subject="Second")
        self.assertEqual(self.search(a["query_no"], self.admin), ["First"])
        self.assertEqual(self.search(b["query_no"].lower(), self.sub), ["Second"])
        self.assertEqual(self.search(f"qry {a['id']}", self.admin), ["First"])
        self.assertEqual(self.search("QRY-9999", self.admin), [])

    def test_a_bare_number_is_not_taken_as_a_query_number(self):
        self.raise_query(self.eng, subject="First")
        self.raise_query(self.eng2, subject="Second")
        c = self.raise_query(self.vendor, subject="Third")
        self.assertEqual(c["id"], 3)
        self.assertEqual(self.search("3", self.admin), [], "only QRY-... counts as a query number (the digit 3 is in no subject or reference)")
        self.assertEqual(self.search("QRY-3", self.admin), ["Third"])

    def test_search_finds_the_day_it_was_raised_in_every_format(self):
        a = self.raise_query(self.eng, subject="Twelfth")
        b = self.raise_query(self.eng2, subject="Fifteenth")
        self.raised_at(a["id"], datetime(2026, 10, 12, 9, 0, tzinfo=timezone.utc))
        self.raised_at(b["id"], datetime(2026, 10, 15, 9, 0, tzinfo=timezone.utc))
        for typed, expect in (("12/10/2026", ["Twelfth"]), ("12-10-2026", ["Twelfth"]), ("2026-10-12", ["Twelfth"]), ("12 Oct 2026", ["Twelfth"]), ("12 October", ["Twelfth"]), ("15 Oct", ["Fifteenth"])):
            self.assertEqual(self.search(typed, self.admin), expect, typed)
        self.assertEqual(self.search("13 Oct", self.admin), [])
        self.assertEqual(self.search("12 Oct 2025", self.admin), [], "a typed year must match")

    def test_the_day_is_the_indian_day(self):
        a = self.raise_query(self.eng, subject="Just after midnight in India")
        b = self.raise_query(self.eng2, subject="Just before midnight in India")
        # 18:45 UTC on the 14th is 00:15 on the 15th in India; 18:15 UTC on the 15th is 23:45 on the 15th in India
        self.raised_at(a["id"], datetime(2026, 10, 14, 18, 45, tzinfo=timezone.utc))
        self.raised_at(b["id"], datetime(2026, 10, 15, 18, 15, tzinfo=timezone.utc))
        self.assertEqual(sorted(self.search("15 Oct 2026", self.admin)), ["Just after midnight in India", "Just before midnight in India"])
        self.assertEqual(self.search("14 Oct 2026", self.admin), [])
        shown = {r["subject"]: r["raised_on"] for r in self.client.get("/api/queries", headers=self.h(self.admin)).json()}
        self.assertEqual(set(shown.values()), {"2026-10-15"})

    def test_search_by_number_or_day_still_respects_who_may_see_the_query(self):
        a = self.raise_query(self.eng, subject="Private")
        self.assertEqual(self.search(a["query_no"], self.eng2), [])
        self.assertEqual(self.search(a["raised_on"], self.eng2), [])
        self.assertEqual(self.search(a["query_no"], self.eng), ["Private"])


if __name__ == "__main__":
    unittest.main()
