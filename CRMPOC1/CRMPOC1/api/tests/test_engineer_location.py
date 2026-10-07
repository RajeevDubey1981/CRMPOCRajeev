from __future__ import annotations

import os
import sys
import unittest
from pathlib import Path

os.environ.setdefault("MYSQL_DATABASE_URL", "sqlite://")
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.database import Base, get_db
from app.main import app
from app.models import User
from app.security import create_access_token, hash_password
from app.seed import seed_roles
from app.services import geo


class GeoTests(unittest.TestCase):
    def test_pincode_and_state_are_cleaned(self):
        self.assertEqual(geo.clean_pincode(" 201 301 "), "201301")
        self.assertIsNone(geo.clean_pincode(""))
        for bad in ("20130", "2013011", "ABCDEF", "012345"):
            with self.assertRaises(ValueError):
                geo.clean_pincode(bad)
        self.assertEqual(geo.canonical_state("uttar pradesh"), "Uttar Pradesh")
        self.assertEqual(geo.canonical_state("ORISSA"), "Odisha")
        self.assertEqual(geo.canonical_state("jammu and kashmir"), "Jammu and Kashmir")
        with self.assertRaises(ValueError):
            geo.canonical_state("Atlantis")

    def test_finding_the_place_in_an_address(self):
        address = "Plot 12, Sector 62, Noida, Gautam Buddh Nagar, Uttar Pradesh 201301"
        self.assertEqual(geo.pincode_in(address), "201301")
        self.assertIsNone(geo.pincode_in("no pin here 12345 or 1234567"))
        self.assertEqual(geo.state_in(address), "Uttar Pradesh")
        self.assertEqual(geo.state_in("Sector 14, Rohini, New Delhi 110085"), "Delhi")

    def test_how_near_an_engineer_is(self):
        address = "Plot 12, Sector 62, Noida, Gautam Buddh Nagar, Uttar Pradesh 201301"
        self.assertEqual(geo.match_engineer(address, "201301", "Uttar Pradesh", "Gautam Buddh Nagar"), "pincode")
        self.assertEqual(geo.match_engineer(address, "201310", "Uttar Pradesh", "Meerut"), "area")
        self.assertEqual(geo.match_engineer(address, "250001", "Uttar Pradesh", "Gautam Buddh Nagar"), "district")
        self.assertEqual(geo.match_engineer(address, "226001", "Uttar Pradesh", "Lucknow"), "state")
        self.assertEqual(geo.match_engineer(address, "302001", "Rajasthan", "Jaipur"), "")
        self.assertEqual(geo.match_engineer(address, None, None, None), "", "an engineer with no place is never nearest")
        self.assertEqual(geo.match_engineer(None, "201301", "Uttar Pradesh", "Noida"), "")


class EngineerLocationApiTests(unittest.TestCase):
    def setUp(self):
        engine = create_engine("sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool)
        Base.metadata.create_all(engine)
        self.Session = sessionmaker(bind=engine, autoflush=False, autocommit=False, future=True)
        self.db = self.Session()
        seed_roles(self.db)

        def override():
            s = self.Session()
            try:
                yield s
            finally:
                s.close()

        app.dependency_overrides[get_db] = override
        self.client = TestClient(app)
        self.admin = self._user("admin@t.com", "admin")
        self.sub = self._user("sub@t.com", "sub_admin")
        self.db.commit()

    def tearDown(self):
        app.dependency_overrides.clear()
        self.db.close()

    def _user(self, email, role):
        u = User(name=email.split("@")[0], email=email, password_hash=hash_password("pw123456"), role=role, is_active=True)
        self.db.add(u)
        self.db.flush()
        return u

    def h(self, user):
        return {"Authorization": f"Bearer {create_access_token(subject=str(user.id), extra_claims={'role': user.role})}"}

    def add(self, name, pin, state, district):
        body = {"name": name, "email": f"{name.lower().replace(' ', '')}@t.com", "password": "pw123456", "role": "engineer"}
        if pin is not None:
            body.update({"pincode": pin, "state": state, "district": district})
        r = self.client.post("/api/users", json=body, headers=self.h(self.admin))
        self.assertEqual(r.status_code, 201, r.text)
        return r.json()

    def engineers(self):
        self.add("Ramesh Kumar", "201301", "uttar pradesh", "Gautam Buddh Nagar")
        self.add("Vikas Sharma", "201310", "Uttar Pradesh", "Gautam Buddh Nagar")
        self.add("Anil Yadav", "226001", "Uttar Pradesh", "Lucknow")
        self.add("Pooja Verma", "302001", "Rajasthan", "Jaipur")
        self.add("No Place", None, None, None)

    def test_place_is_saved_checked_and_can_be_cleared(self):
        eng = self.add("Ramesh Kumar", "201 301", "uttar pradesh", "  Gautam   Buddh Nagar ")
        self.assertEqual((eng["pincode"], eng["state"], eng["district"]), ("201301", "Uttar Pradesh", "Gautam Buddh Nagar"))
        base = {"name": "X", "email": "x@t.com", "password": "pw123456", "role": "engineer"}
        for bad in ({"pincode": "2013"}, {"pincode": "20130A"}, {"state": "Atlantis"}):
            self.assertEqual(self.client.post("/api/users", json={**base, **bad}, headers=self.h(self.admin)).status_code, 422, bad)
        moved = self.client.put(f"/api/users/{eng['id']}", json={"pincode": "302001", "state": "Rajasthan", "district": "Jaipur"}, headers=self.h(self.admin))
        self.assertEqual((moved.json()["pincode"], moved.json()["district"]), ("302001", "Jaipur"))
        other = self.client.put(f"/api/users/{eng['id']}", json={"phone": "9999999999"}, headers=self.h(self.admin))
        self.assertEqual(other.json()["pincode"], "302001", "changing something else leaves the place alone")
        cleared = self.client.put(f"/api/users/{eng['id']}", json={"pincode": "", "state": "", "district": ""}, headers=self.h(self.admin))
        self.assertEqual((cleared.json()["pincode"], cleared.json()["state"], cleared.json()["district"]), (None, None, None))
        self.assertEqual(self.client.put(f"/api/users/{eng['id']}", json={"pincode": "123"}, headers=self.h(self.sub)).status_code, 422)

    def test_search_engineers_by_pin_code_state_or_district(self):
        self.engineers()

        def names(**p):
            rows = self.client.get("/api/users", params={"role": "engineer", **p}, headers=self.h(self.admin)).json()
            return sorted(u["name"] for u in rows)

        self.assertEqual(names(pincode="201301"), ["Ramesh Kumar"])
        self.assertEqual(names(pincode="2013"), ["Ramesh Kumar", "Vikas Sharma"], "the first digits of a pin code find the area")
        self.assertEqual(names(state="Rajasthan"), ["Pooja Verma"])
        self.assertEqual(names(state="uttar pradesh"), ["Anil Yadav", "Ramesh Kumar", "Vikas Sharma"])
        self.assertEqual(names(district="buddh"), ["Ramesh Kumar", "Vikas Sharma"])
        self.assertEqual(names(state="Uttar Pradesh", district="lucknow"), ["Anil Yadav"])
        self.assertEqual(names(search="jaipur"), ["Pooja Verma"], "the name box also finds a district")
        self.assertEqual(names(search="226001"), ["Anil Yadav"])
        self.assertEqual(len(names()), 5)

    def test_assign_list_puts_the_nearest_engineers_first(self):
        self.engineers()
        url = "/api/installations/engineer-assignment-options"
        address = "Plot 12, Sector 62, Noida, Gautam Buddh Nagar, Uttar Pradesh 201301"
        rows = self.client.get(url, params={"address": address}, headers=self.h(self.admin)).json()
        self.assertEqual([(r["name"], r["match"]) for r in rows[:3]], [("Ramesh Kumar", "pincode"), ("Vikas Sharma", "area"), ("Anil Yadav", "state")])
        self.assertEqual({r["match"] for r in rows[3:]}, {""})
        self.assertEqual(rows[0]["pincode"], "201301")
        plain = self.client.get(url, headers=self.h(self.admin)).json()
        self.assertEqual([r["name"] for r in plain], sorted(r["name"] for r in plain), "without an address the list is as before")
        self.assertEqual({r["match"] for r in plain}, {""})

    def test_customer_place_is_saved_and_decides_the_nearest(self):
        self.engineers()
        cc = self._user("cc@t.com", "callcenter")
        self.db.commit()
        # no pin code in the address text: the typed place does the work
        base = {"customer_name": "Asha", "customer_mobile": "9876543210", "customer_address": "Flat 4, Green Park"}
        r = self.client.post("/api/complaints", json={**base, "pincode": "226 001", "state": "uttar pradesh", "district": "Lucknow", "query_type": "Service"}, headers=self.h(self.admin))
        self.assertEqual(r.status_code, 201, r.text)
        self.assertEqual((r.json()["pincode"], r.json()["state"], r.json()["district"]), ("226001", "Uttar Pradesh", "Lucknow"))
        bad = self.client.post("/api/complaints", json={**base, "pincode": "22", "query_type": "Service"}, headers=self.h(self.admin))
        self.assertEqual(bad.status_code, 422)
        edited = self.client.put(f"/api/complaints/{r.json()['id']}", json={"pincode": "", "state": "", "district": ""}, headers=self.h(self.admin))
        self.assertEqual((edited.json()["pincode"], edited.json()["state"], edited.json()["district"]), (None, None, None))

        svc = self.client.post("/api/services", json={**base, "pincode": "302001", "state": "Rajasthan", "district": "Jaipur"}, headers=self.h(cc))
        self.assertEqual(svc.status_code, 201, svc.text)
        self.assertEqual(svc.json()["district"], "Jaipur")

        inst = self.client.post("/api/installations", json={"customer_name": "Asha", "contact_number": "9876543210", "address": "Flat 4", "pincode": "201301", "state": "Uttar Pradesh", "district": "Gautam Buddh Nagar", "source": "callcenter"}, headers=self.h(self.admin))
        self.assertEqual(inst.status_code, 201, inst.text)
        self.assertEqual(inst.json()["pincode"], "201301")

        url = "/api/installations/engineer-assignment-options"
        rows = self.client.get(url, params={"pincode": "226001", "state": "Uttar Pradesh", "district": "Lucknow"}, headers=self.h(self.admin)).json()
        self.assertEqual([(r["name"], r["match"]) for r in rows[:3]], [("Anil Yadav", "pincode"), ("Ramesh Kumar", "state"), ("Vikas Sharma", "state")])
        jaipur = self.client.get(url, params={"state": "Rajasthan", "district": "jaipur"}, headers=self.h(self.admin)).json()
        self.assertEqual((jaipur[0]["name"], jaipur[0]["match"]), ("Pooja Verma", "district"))
        junk = self.client.get(url, params={"pincode": "12", "state": "Atlantis"}, headers=self.h(self.admin))
        self.assertEqual(junk.status_code, 200, "a wrong place is ignored, not an error")


if __name__ == "__main__":
    unittest.main()
