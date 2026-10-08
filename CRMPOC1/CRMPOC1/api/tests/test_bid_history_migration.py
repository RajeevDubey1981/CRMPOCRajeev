import importlib.util
import sys
import unittest
from pathlib import Path

import sqlalchemy as sa
from alembic.migration import MigrationContext
from alembic.operations import Operations

API = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(API))


def _load_migration():
    spec = importlib.util.spec_from_file_location("m57", API / "alembic" / "versions" / "0057_hide_override_remarks.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


class HideOverrideRemarksMigrationTests(unittest.TestCase):
    def setUp(self):
        self.engine = sa.create_engine("sqlite://")
        with self.engine.begin() as c:
            c.execute(sa.text("create table vendors (id integer primary key, name_of_firm text)"))
            c.execute(sa.text(
                "create table bid_events (id integer primary key autoincrement, bid_id integer, at text, actor_name text, "
                "actor_user_id integer, action text, text text, vendor_id integer)"))
            c.execute(sa.text("insert into vendors values (1, 'KAMINI DISTRIBUTORS'), (2, 'NISNIK INTERNATIONAL')"))
            rows = [
                (5, "2026-10-06", "Administrator", 9, "override", "ADMIN OVERRIDE: reassigned from KAMINI DISTRIBUTORS to NISNIK INTERNATIONAL. Reason: Vendor technical mismatch. Confirm by 7 Oct 2026, submit by 7 Oct 2026", 2),
                (5, "2026-10-06", "Administrator", 9, "taken_back", "Taken back from KAMINI DISTRIBUTORS", 1),
                (5, "2026-10-07", "Neha", 8, "released", "Released: Customer changed the specification. The bid is free for allocation again", 2),
                (5, "2026-10-07", "Cool Zone", 7, "released", "Released: Cool Zone declined: no stock. The bid is free for allocation again", 3),
                (5, "2026-10-07", "System", None, "auto_released", "Released: Frost did not confirm by 7 Oct 2026. The bid is free for allocation again", 1),
            ]
            for r in rows:
                c.execute(sa.text("insert into bid_events (bid_id, at, actor_name, actor_user_id, action, text, vendor_id) values (:a,:b,:c,:d,:e,:f,:g)"),
                          dict(zip("abcdefg", r)))

    def run_up(self):
        mod = _load_migration()
        with self.engine.begin() as conn:
            with Operations.context(MigrationContext.configure(conn)):
                mod.upgrade()

    def vendor_text(self):
        with self.engine.connect() as c:
            return [r[0] for r in c.execute(sa.text("select text from bid_events where vendor_id is not null order by id"))]

    def test_vendors_no_longer_see_the_remarks_and_the_team_keeps_them(self):
        self.run_up()
        seen = " | ".join(self.vendor_text())
        for secret in ("KAMINI DISTRIBUTORS to", "OVERRIDE", "mismatch", "specification", "Taken back from"):
            self.assertNotIn(secret, seen)
        self.assertIn("Allocated to NISNIK INTERNATIONAL. Confirm by 7 Oct 2026", seen)
        self.assertIn("Taken back by INDcool", seen)
        self.assertIn("Released by INDcool", seen)
        self.assertIn("declined: no stock", seen, "a vendor's own decline stays as it was")
        self.assertIn("did not confirm", seen)
        with self.engine.connect() as c:
            team = " | ".join(r[0] for r in c.execute(sa.text("select text from bid_events where vendor_id is null")))
        self.assertIn("ADMIN OVERRIDE: reassigned from KAMINI DISTRIBUTORS to NISNIK INTERNATIONAL. Reason: Vendor technical mismatch", team)
        self.assertIn("Customer changed the specification", team)

    def test_running_it_twice_changes_nothing_more(self):
        self.run_up()
        with self.engine.connect() as c:
            first = c.execute(sa.text("select count(*) from bid_events")).scalar()
        self.run_up()
        with self.engine.connect() as c:
            self.assertEqual(c.execute(sa.text("select count(*) from bid_events")).scalar(), first)


if __name__ == "__main__":
    unittest.main()
