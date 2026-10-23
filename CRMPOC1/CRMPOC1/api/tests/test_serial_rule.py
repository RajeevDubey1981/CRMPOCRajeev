from __future__ import annotations

import os
import sys
import unittest
from pathlib import Path

os.environ.setdefault("MYSQL_DATABASE_URL", "sqlite://")
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from fastapi import HTTPException
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.database import Base
from app.models.item_master import ItemMaster
from app.models.order import OrderItem
from app.services.service_unit_workflow import apply_serial_rule, clean_serial, product_serial_count


class SerialRuleTests(unittest.TestCase):
    """A product carries the number of serials its item master says: one for a window AC or refrigerator, two for a split AC."""

    def setUp(self):
        engine = create_engine("sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool)
        Base.metadata.create_all(engine)
        self.db = sessionmaker(bind=engine, future=True)()

    def master(self, code, count):
        m = ItemMaster(item_code=code, item_name=code, serial_count=count)
        self.db.add(m)
        self.db.flush()
        return m

    def line(self, master, serial1="S1", serial2=None):
        row = OrderItem(order_id=1, item_id=master.id, item_code=master.item_code, serial_no=serial1, serial_no_2=serial2)
        return row

    def test_placeholders_are_not_serials(self):
        for junk in ("0", " 0 ", "-", "NA", "n/a", "None", "", None):
            self.assertIsNone(clean_serial(junk), repr(junk))
        self.assertEqual(clean_serial(" ABC123 "), "ABC123")
        self.assertEqual(clean_serial("0123"), "0123", "a real serial that starts with 0 stays")

    def test_one_serial_product_never_keeps_a_second_serial(self):
        window = self.line(self.master("WAC", 1))
        self.assertEqual(product_serial_count(self.db, window), 1)
        self.assertIsNone(apply_serial_rule(self.db, window, None))
        self.assertIsNone(apply_serial_rule(self.db, window, "0"), "the demo 0 is dropped")
        self.assertIsNone(apply_serial_rule(self.db, window, "OTHER"), "a one-serial product has no second serial")

    def test_two_serial_product_needs_both(self):
        split = self.line(self.master("SAC", 2))
        self.assertEqual(product_serial_count(self.db, split), 2)
        self.assertEqual(apply_serial_rule(self.db, split, "IND-2"), "IND-2")
        for missing in (None, "", "0"):
            with self.assertRaises(HTTPException) as ctx:
                apply_serial_rule(self.db, split, missing)
            self.assertEqual(ctx.exception.status_code, 400)
            self.assertIn("2 serial numbers", ctx.exception.detail)

    def test_two_serial_product_takes_the_second_serial_from_the_order_line(self):
        split = self.line(self.master("SAC2", 2), serial2="IND-OUT")
        self.assertEqual(apply_serial_rule(self.db, split, None), "IND-OUT")


if __name__ == "__main__":
    unittest.main()
