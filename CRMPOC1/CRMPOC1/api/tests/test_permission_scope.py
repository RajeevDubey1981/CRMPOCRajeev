from __future__ import annotations

import os
import sys
import unittest
from pathlib import Path

os.environ.setdefault("MYSQL_DATABASE_URL", "sqlite://")
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.database import Base
from app.models import Permission, Role, User
from app.services.permissions import can_act_on, sub_module_scope

TYPES = ("Service", "Installation", "Sales", "Others")


class SubModuleScopeTests(unittest.TestCase):
    def setUp(self):
        engine = create_engine("sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool)
        Base.metadata.create_all(engine)
        self.db = sessionmaker(bind=engine, future=True)()

    def tearDown(self):
        self.db.close()

    def role(self, name, whole, ticked):
        """A role whose whole-module Complaints box is `whole` and whose sub-module boxes are ticked for `ticked`."""
        r = Role(name=name, description=name)
        self.db.add(r)
        self.db.flush()
        self.db.add(Permission(role_id=r.id, module="complaints", sub_module=None, can_view=whole, can_edit=whole))
        for t in TYPES:
            self.db.add(Permission(role_id=r.id, module="complaints", sub_module=t, can_view=t in ticked, can_edit=t in ticked))
        u = User(name=name, email=f"{name}@t.com", password_hash="x", role=name, is_active=True)
        self.db.add(u)
        self.db.commit()
        return u

    def test_the_whole_module_tick_with_a_sub_module_unticked_keeps_that_sub_module_out(self):
        u = self.role("indcool_service", True, {"Service", "Installation", "Others"})
        self.assertEqual(sub_module_scope(self.db, u, "complaints", "can_view"), {"Service", "Installation", "Others"})
        self.assertFalse(can_act_on(self.db, u, "complaints", "can_view", "Sales"))
        self.assertTrue(can_act_on(self.db, u, "complaints", "can_view", "Service"))
        self.assertEqual(sub_module_scope(self.db, u, "complaints", "can_edit"), {"Service", "Installation", "Others"})

    def test_all_ticked_or_all_unticked_sub_modules_keep_the_whole_module_meaning(self):
        admin = self.role("admin", True, set(TYPES))
        self.assertIsNone(sub_module_scope(self.db, admin, "complaints", "can_view"))
        engineer = self.role("engineer", True, set())
        self.assertIsNone(sub_module_scope(self.db, engineer, "complaints", "can_view"))

    def test_no_whole_module_tick_uses_the_ticked_sub_modules(self):
        u = self.role("viewer", False, {"Service"})
        self.assertEqual(sub_module_scope(self.db, u, "complaints", "can_view"), {"Service"})
        nobody = self.role("vendor", False, set())
        self.assertEqual(sub_module_scope(self.db, nobody, "complaints", "can_view"), set())


if __name__ == "__main__":
    unittest.main()
