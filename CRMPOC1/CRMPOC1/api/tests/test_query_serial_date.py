from __future__ import annotations

import unittest

import test_queries as _q


class QuerySerialDateTests(unittest.TestCase):
    # the same database, users and helpers as the Queries tests
    setUp = _q.QueriesTests.setUp
    tearDown = _q.QueriesTests.tearDown
    _user = _q.QueriesTests._user
    h = _q.QueriesTests.h

    def raise_with(self, who, serial=None, date=None, subject="AC INSTALLATION"):
        body = {"subject": subject, "category": "Installation", "related_to": "GEMC-511687749197919", "message": "Please check", "serial_no": serial, "query_date": date}
        r = self.client.post("/api/queries", json=body, headers=self.h(who))
        return r

    def search(self, text, who):
        r = self.client.get("/api/queries", params={"search": text}, headers=self.h(who))
        self.assertEqual(r.status_code, 200, r.text)
        return [row["subject"] for row in r.json()]

    def test_serial_number_and_date_are_kept_and_shown(self):
        r = self.raise_with(self.eng, serial="  AC2610012345 ", date="2026-10-12")
        self.assertEqual(r.status_code, 201, r.text)
        d = r.json()
        self.assertEqual((d["serial_no"], d["query_date"]), ("AC2610012345", "2026-10-12"))
        row = self.client.get("/api/queries", headers=self.h(self.admin)).json()[0]
        self.assertEqual((row["serial_no"], row["query_date"]), ("AC2610012345", "2026-10-12"))

    def test_both_are_optional_and_bad_values_are_refused(self):
        d = self.raise_with(self.eng).json()
        self.assertEqual((d["serial_no"], d["query_date"]), (None, None))
        d = self.raise_with(self.eng, serial="   ", date="").json()
        self.assertEqual((d["serial_no"], d["query_date"]), (None, None), "empty boxes stay empty")
        self.assertEqual(self.raise_with(self.eng, date="1990-01-01").status_code, 422)
        self.assertEqual(self.raise_with(self.eng, date="not a date").status_code, 422)

    def test_search_finds_a_serial_number_even_part_of_it(self):
        self.raise_with(self.eng, serial="AC2610012345", subject="First")
        self.raise_with(self.eng2, serial="AC2610008871", subject="Second")
        self.assertEqual(self.search("AC2610012345", self.admin), ["First"])
        self.assertEqual(self.search("ac26100088", self.sub), ["Second"])
        self.assertEqual(sorted(self.search("AC26100", self.admin)), ["First", "Second"])
        self.assertEqual(self.search("AC9999", self.admin), [])

    def test_search_understands_a_typed_date(self):
        self.raise_with(self.eng, date="2026-10-12", subject="Twelfth")
        self.raise_with(self.eng2, date="2026-11-12", subject="November twelfth")
        self.raise_with(self.vendor, date="2025-10-12", subject="Last year")
        for typed, expect in (
            ("12/10/2026", ["Twelfth"]),
            ("12-10-2026", ["Twelfth"]),
            ("2026-10-12", ["Twelfth"]),
            ("12 Oct 2026", ["Twelfth"]),
            ("12 October 2026", ["Twelfth"]),
        ):
            self.assertEqual(self.search(typed, self.admin), expect, typed)
        self.assertEqual(sorted(self.search("12 Oct", self.admin)), ["Last year", "Twelfth"], "without a year: every 12 October")
        self.assertEqual(self.search("13 Oct", self.admin), [])

    def test_search_still_respects_who_may_see_the_query(self):
        self.raise_with(self.eng, serial="AC2610012345")
        self.assertEqual(self.search("AC2610012345", self.eng2), [], "another engineer does not see it")
        self.assertEqual(self.search("AC2610012345", self.eng), ["AC INSTALLATION"])

    def test_the_owner_and_the_admin_team_can_change_them_and_it_goes_to_the_history(self):
        q = self.raise_with(self.eng, serial="AC2610012345", date="2026-10-12").json()
        self.assertTrue(q["can_edit_details"])
        r = self.client.put(f"/api/queries/{q['id']}/details", json={"serial_no": "AC2610012346", "query_date": "2026-10-14"}, headers=self.h(self.eng))
        self.assertEqual(r.status_code, 200, r.text)
        d = r.json()
        self.assertEqual((d["serial_no"], d["query_date"]), ("AC2610012346", "2026-10-14"))
        text = [e["text"] for e in self.client.get(f"/api/queries/{q['id']}", headers=self.h(self.sub)).json()["events"] if e["kind"] == "details"][0]
        self.assertIn("AC2610012346 (was AC2610012345)", text)
        self.assertIn("14 Oct 2026 (was 12 Oct 2026)", text)
        # the Admin team can change it too, and clear it
        r = self.client.put(f"/api/queries/{q['id']}/details", json={"serial_no": None, "query_date": None}, headers=self.h(self.sub))
        self.assertEqual((r.json()["serial_no"], r.json()["query_date"]), (None, None))
        # saving the same thing again writes nothing new
        before = len(self.client.get(f"/api/queries/{q['id']}", headers=self.h(self.admin)).json()["events"])
        self.client.put(f"/api/queries/{q['id']}/details", json={"serial_no": None, "query_date": None}, headers=self.h(self.admin))
        after = len(self.client.get(f"/api/queries/{q['id']}", headers=self.h(self.admin)).json()["events"])
        self.assertEqual(before, after)

    def test_someone_else_cannot_change_them(self):
        q = self.raise_with(self.eng, serial="AC2610012345").json()
        r = self.client.put(f"/api/queries/{q['id']}/details", json={"serial_no": "X"}, headers=self.h(self.eng2))
        self.assertEqual(r.status_code, 404, "cannot even see it")
        # forwarded to someone: they hold it but did not raise it
        self.client.post(f"/api/queries/{q['id']}/forward", json={"to_user_id": self.tech.id}, headers=self.h(self.sub))
        seen = self.client.get(f"/api/queries/{q['id']}", headers=self.h(self.tech)).json()
        self.assertFalse(seen["can_edit_details"])
        r = self.client.put(f"/api/queries/{q['id']}/details", json={"serial_no": "X"}, headers=self.h(self.tech))
        self.assertEqual(r.status_code, 403, r.text)


if __name__ == "__main__":
    unittest.main()
