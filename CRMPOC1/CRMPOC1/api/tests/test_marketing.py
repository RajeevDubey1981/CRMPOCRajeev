"""Marketing, release 1: its own database, the role, the user tick, the menu and the ticks inside Marketing."""
from __future__ import annotations

import os
import sys
import unittest
from pathlib import Path

os.environ.setdefault("MYSQL_DATABASE_URL", "sqlite://")
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from fastapi.testclient import TestClient
from sqlalchemy import create_engine, inspect
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.database import Base, get_db
from app.main import app
from app.marketing.db import MarketingBase, get_marketing_db, use_factory
from app.models import Permission, Role, User
from app.security import create_access_token, hash_password


def sqlite_engine():
    return create_engine("sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool)


class MarketingTests(unittest.TestCase):
    def setUp(self):
        self.main_engine, self.mk_engine = sqlite_engine(), sqlite_engine()
        Base.metadata.create_all(self.main_engine)
        MarketingBase.metadata.create_all(self.mk_engine)
        self.Main = sessionmaker(bind=self.main_engine, autoflush=False, autocommit=False, future=True)
        self.Mk = sessionmaker(bind=self.mk_engine, autoflush=False, autocommit=False, future=True)
        use_factory(self.Mk, self.mk_engine)
        self.db = self.Main()

        def main_override():
            s = self.Main()
            try:
                yield s
            finally:
                s.close()

        def mk_override():
            s = self.Mk()
            try:
                yield s
            finally:
                s.close()

        app.dependency_overrides[get_db] = main_override
        app.dependency_overrides[get_marketing_db] = mk_override
        self.client = TestClient(app)
        for name in ("admin", "sub_admin", "sales", "sales_manager", "marketing", "callcenter", "engineer", "vendor"):
            r = Role(name=name, description=name)
            self.db.add(r)
            self.db.flush()
            if name in ("admin", "sub_admin"):
                self.db.add(Permission(role_id=r.id, module="users", can_view=True, can_create=True, can_edit=True, can_delete=True, can_export=True))
        self.admin = self._user("admin@t.com", "admin", "Admin")
        self.sub = self._user("sub@t.com", "sub_admin", "Sub Admin")
        self.team = self._user("team@t.com", "sales", "Amit Team")
        self.mgr = self._user("mgr@t.com", "sales_manager", "Karan Manager")
        self.mkt = self._user("mkt@t.com", "marketing", "Rohit Marketing")
        self.cc = self._user("cc@t.com", "callcenter", "Call Centre")
        self.eng = self._user("eng@t.com", "engineer", "Ramesh Engineer")
        self.db.commit()

    def tearDown(self):
        use_factory(None, None)
        app.dependency_overrides.clear()
        self.db.close()

    def _user(self, email, role, name):
        u = User(name=name, email=email, password_hash=hash_password("pw123456"), role=role, is_active=True)
        self.db.add(u)
        self.db.flush()
        return u

    def h(self, user):
        return {"Authorization": f"Bearer {create_access_token(subject=str(user.id), extra_claims={'role': user.role})}"}

    def get(self, url, who):
        return self.client.get(url, headers=self.h(who))

    def put(self, url, body, who):
        return self.client.put(url, json=body, headers=self.h(who))

    def menu(self, who) -> bool:
        me = self.get("/api/auth/me", who).json()
        return any(p["module"] == "marketing" and p["can_view"] for p in me["permissions"])

    def tick(self, user, value):
        r = self.put(f"/api/users/{user.id}", {"can_manage_marketing": value}, self.admin)
        self.assertEqual(r.status_code, 200, r.text)
        return r.json()

    # ---- who has the menu ----
    def test_the_menu_is_for_admin_sub_admin_the_marketing_role_and_people_with_the_tick(self):
        self.assertTrue(self.menu(self.admin) and self.menu(self.sub) and self.menu(self.mkt))
        for u in (self.team, self.mgr, self.cc):
            self.assertFalse(self.menu(u), u.name)
        self.assertTrue(self.tick(self.mgr, True)["can_manage_marketing"])
        self.assertTrue(self.menu(self.mgr))
        self.assertFalse(self.menu(self.team), "a tick on one person does not reach another")
        self.tick(self.mgr, False)
        self.assertFalse(self.menu(self.mgr))

    def test_engineers_and_vendors_cannot_be_given_marketing(self):
        self.assertFalse(self.tick(self.eng, True)["can_manage_marketing"])
        self.assertFalse(self.menu(self.eng))
        self.assertEqual(self.get("/api/marketing/status", self.eng).status_code, 403)

    def test_nobody_has_the_menu_while_the_marketing_database_is_not_set_up(self):
        use_factory(None, None)
        try:
            self.assertFalse(self.menu(self.admin))
            self.assertFalse(self.menu(self.mkt))
            self.assertEqual(self.client.get("/api/marketing/enabled", headers=self.h(self.admin)).json(), {"enabled": False})
        finally:
            use_factory(self.Mk, self.mk_engine)
        self.assertEqual(self.client.get("/api/marketing/enabled", headers=self.h(self.admin)).json(), {"enabled": True})

    def test_the_role_exists_and_the_user_form_can_make_a_marketing_user(self):
        r = self.client.post("/api/users", json={"name": "New Mkt", "email": "newmkt@t.com", "password": "pw123456", "role": "marketing"}, headers=self.h(self.admin))
        self.assertEqual(r.status_code, 201, r.text)
        new = self.db.get(User, r.json()["id"])
        self.assertTrue(self.menu(new))

    # ---- ticks inside Marketing ----
    def test_default_ticks_by_kind_of_person(self):
        for who, expect, absent in (
            (self.admin, {"view", "approve", "connect", "settings", "give_ticks"}, set()),
            (self.mkt, {"view", "aud_all", "approve", "cost", "upload", "consent_edit"}, {"connect", "settings", "give_ticks"}),
        ):
            t = set(self.get("/api/marketing/status", who).json()["ticks"])
            self.assertTrue(expect <= t, (who.name, expect - t))
            self.assertFalse(absent & t, (who.name, absent & t))
        self.tick(self.team, True)
        self.tick(self.mgr, True)
        team = set(self.get("/api/marketing/status", self.team).json()["ticks"])
        mgr = set(self.get("/api/marketing/status", self.mgr).json()["ticks"])
        self.assertEqual(team, {"view", "aud_own", "draft", "submit"})
        self.assertTrue({"aud_all", "approve", "cost", "upload"} <= mgr)
        self.assertNotIn("consent_edit", mgr)

    def test_admin_changes_ticks_for_a_kind_and_for_one_person_with_a_history(self):
        self.tick(self.team, True)
        self.tick(self.cc, True)
        # for the whole Sales Team kind
        r = self.put("/api/marketing/ticks/role/team", {"ticks": {"approve": True}}, self.admin)
        self.assertEqual(r.status_code, 200, r.text)
        self.assertIn("approve", r.json()["ticks"])
        self.assertIn("approve", self.get("/api/marketing/status", self.team).json()["ticks"])
        self.assertNotIn("approve", self.get("/api/marketing/status", self.cc).json()["ticks"], "the Others kind is not changed")
        # for one person, against their kind
        self.put(f"/api/marketing/ticks/user/{self.team.id}", {"ticks": {"approve": False, "cost": True}}, self.admin)
        t = set(self.get("/api/marketing/status", self.team).json()["ticks"])
        self.assertTrue("cost" in t and "approve" not in t)
        # back to the default
        self.put(f"/api/marketing/ticks/user/{self.team.id}", {"ticks": {"approve": None, "cost": None}}, self.admin)
        self.put("/api/marketing/ticks/role/team", {"ticks": {"approve": None}}, self.admin)
        self.assertEqual(set(self.get("/api/marketing/status", self.team).json()["ticks"]), {"view", "aud_own", "draft", "submit"})
        hist = self.get("/api/marketing/ticks/history", self.admin).json()
        self.assertTrue(hist and all(x["by"] == "Admin" for x in hist))
        self.assertTrue(any(x["person"] == "Amit Team" for x in hist))

    def test_locked_ticks_and_who_may_change_ticks(self):
        self.tick(self.team, True)
        self.assertEqual(self.put("/api/marketing/ticks/role/team", {"ticks": {"connect": True}}, self.admin).status_code, 400)
        self.assertEqual(self.put(f"/api/marketing/ticks/user/{self.team.id}", {"ticks": {"settings": True}}, self.admin).status_code, 400)
        self.assertEqual(self.put("/api/marketing/ticks/role/team", {"ticks": {"nonsense": True}}, self.admin).status_code, 400)
        self.assertEqual(self.put("/api/marketing/ticks/role/team", {"ticks": {"approve": True}}, self.mkt).status_code, 403)
        self.assertEqual(self.get("/api/marketing/ticks", self.mkt).status_code, 403)
        self.assertEqual(self.put(f"/api/marketing/ticks/user/{self.admin.id}", {"ticks": {"cost": False}}, self.admin).status_code, 400, "nobody ticks for themselves")
        self.assertEqual(self.put("/api/marketing/ticks/role/nobody", {"ticks": {}}, self.admin).status_code, 404)
        catalog = self.get("/api/marketing/ticks", self.sub).json()
        self.assertEqual([k["key"] for k in catalog["kinds"]], ["mkt", "mgr", "team", "oth"])
        names = {p["name"] for p in catalog["people"]}
        self.assertTrue({"Amit Team", "Karan Manager", "Rohit Marketing"} <= names)
        self.assertNotIn("Ramesh Engineer", names)

    def test_settings_are_for_admin_and_sub_admin(self):
        self.assertEqual(self.put("/api/marketing/settings", {"rate_sms": 0.25}, self.mkt).status_code, 403)
        r = self.put("/api/marketing/settings", {"rate_sms": 0.25, "monthly_cap": 3}, self.sub)
        self.assertEqual(r.status_code, 200, r.text)
        self.assertEqual((r.json()["rate_sms"], r.json()["monthly_cap"], r.json()["rate_whatsapp"]), ("0.25", "3", "0.90"))
        self.assertEqual(self.put("/api/marketing/settings", {"rate_sms": -1}, self.admin).status_code, 400)
        self.assertEqual(self.get("/api/marketing/status", self.mkt).json()["settings"]["rate_sms"], "0.25", "the Marketing role sees the cost")

    def test_the_marketing_tables_live_only_in_the_marketing_database(self):
        mk = {t for t in inspect(self.mk_engine).get_table_names()}
        crm = {t for t in inspect(self.main_engine).get_table_names()}
        self.assertTrue({"mk_profile", "mk_role_tick", "mk_user_tick", "mk_tick_history", "mk_setting"} <= mk)
        self.assertFalse([t for t in crm if t.startswith("mk_")])
        self.assertFalse([t for t in mk if t in crm])

    def test_the_marketing_database_update_creates_the_tables(self):
        from alembic.config import Config
        from alembic.runtime.migration import MigrationContext
        from alembic.script import ScriptDirectory

        cfg = Config(str(Path(__file__).resolve().parents[1] / "alembic_marketing.ini"))
        cfg.set_main_option("script_location", str(Path(__file__).resolve().parents[1] / "marketing_alembic"))
        heads = ScriptDirectory.from_config(cfg).get_heads()
        self.assertEqual(heads, ["0001_marketing_initial"])

    def test_a_pymysql_url_is_read_as_the_projects_mysql_driver_and_a_bad_url_never_stops_the_crm(self):
        from app.config import Settings

        got = Settings(marketing_database_url="mysql+pymysql://indcool_mk:abc@localhost/indcool_marketing").marketing_database_url
        self.assertEqual(got, "mysql+mysqlconnector://indcool_mk:abc@localhost/indcool_marketing")
        self.assertEqual(Settings(marketing_database_url="").marketing_database_url, "")
        from app.marketing import db as mkdb
        from app.config import settings

        old = settings.marketing_database_url
        try:
            settings.marketing_database_url = "notadriver://x:y@localhost/z"
            self.assertEqual(mkdb._build(), (None, None))
        finally:
            settings.marketing_database_url = old


if __name__ == "__main__":
    unittest.main()
