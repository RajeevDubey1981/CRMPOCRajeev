from __future__ import annotations

import unittest
from unittest.mock import patch

import test_queries as _q

from app.services import pincode_lookup as pl


class FakeResponse:
    def __init__(self, data):
        self._data = data

    def json(self):
        return self._data


def post_offices(state, district, names=("Port Blair", "Bathu Basti"), block="South Andaman"):
    return [{"Status": "Success", "PostOffice": [{"Name": n, "District": district, "State": state, "Block": block, "Division": "x"} for n in names]}]


class PincodeTests(unittest.TestCase):
    # the same database and client as the Queries tests
    setUp = _q.QueriesTests.setUp
    tearDown = _q.QueriesTests.tearDown
    _user = _q.QueriesTests._user

    def setUp(self):  # noqa: F811
        _q.QueriesTests.setUp(self)
        pl._kept.clear()

    def get(self, pin):
        return self.client.get(f"/api/places/pincode/{pin}")  # public: no login

    def test_a_pin_code_gives_state_and_district_in_the_spelling_of_our_lists(self):
        with patch.object(pl.requests, "get", return_value=FakeResponse(post_offices("Andaman & Nicobar Islands", "South Andaman"))):
            r = self.get("744106")
        self.assertEqual(r.status_code, 200, r.text)
        d = r.json()
        self.assertEqual((d["state"], d["district"], d["city"]), ("Andaman and Nicobar Islands", "South Andaman", "South Andaman"))
        self.assertIn("Port Blair", d["places"])

    def test_old_names_of_states_are_turned_into_the_names_in_the_list(self):
        for raw, want, pin in (("Pondicherry", "Puducherry", "605001"), ("Orissa", "Odisha", "751001"), ("Dadra & Nagar Haveli", "Dadra and Nagar Haveli and Daman and Diu", "396230"),
                               ("Jammu & Kashmir", "Jammu and Kashmir", "180001"), ("Delhi", "Delhi", "110001")):
            pl._kept.clear()
            with patch.object(pl.requests, "get", return_value=FakeResponse(post_offices(raw, "X"))):
                self.assertEqual(self.get(pin).json()["state"], want, raw)

    def test_a_pin_code_that_does_not_exist_and_a_bad_one(self):
        with patch.object(pl.requests, "get", return_value=FakeResponse([{"Status": "Error", "PostOffice": None}])):
            self.assertEqual(self.get("999999").status_code, 404)
        for bad in ("12345", "0123456", "abcdef", "12345a"):
            self.assertEqual(self.get(bad).status_code, 400, bad)

    def test_when_india_post_does_not_answer_the_first_digits_give_the_state_where_they_are_clear(self):
        with patch.object(pl.requests, "get", side_effect=RuntimeError("no network")):
            self.assertEqual(self.get("744106").json()["state"], "Andaman and Nicobar Islands")
            self.assertEqual(self.get("403001").json()["state"], "Goa")
            self.assertEqual(self.get("682301").json()["state"], "Kerala")
            self.assertEqual(self.get("226001").status_code, 404, "Uttar Pradesh and Uttarakhand share these digits: no guess")

    def test_an_answer_is_kept_so_india_post_is_asked_once(self):
        with patch.object(pl.requests, "get", return_value=FakeResponse(post_offices("Goa", "North Goa"))) as m:
            self.get("403001")
            self.get("403001")
            self.assertEqual(m.call_count, 1)


if __name__ == "__main__":
    unittest.main()
