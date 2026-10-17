from __future__ import annotations

import os
import sys
import unittest
from datetime import date
from pathlib import Path

os.environ.setdefault("MYSQL_DATABASE_URL", "sqlite://")
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.database import Base
from app.models import Order, OrderItem
from app.routers.installation_callcenter import _order_item_for_serial_pair


class InstallationOrderSerialTests(unittest.TestCase):
    def setUp(self):
        engine = create_engine("sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool)
        Base.metadata.create_all(engine)
        self.db = sessionmaker(bind=engine, future=True)()
        first = Order(order_no="GEM-ONE", order_date=date.today())
        second = Order(order_no="GEM-TWO", order_date=date.today())
        self.db.add_all([first, second])
        self.db.flush()
        self.first_item = OrderItem(order_id=first.id, serial_no="SERIAL-A", serial_no_2="SERIAL-B")
        self.same_order_item = OrderItem(order_id=first.id, serial_no="SERIAL-C", serial_no_2="SERIAL-D")
        self.second_item = OrderItem(order_id=second.id, serial_no="SERIAL-X", serial_no_2="SERIAL-Y")
        self.db.add_all([self.first_item, self.same_order_item, self.second_item])
        self.db.commit()
        self.first_order_id = first.id

    def tearDown(self):
        self.db.close()

    def test_matches_pair_on_same_order_row_case_insensitively(self):
        matched = _order_item_for_serial_pair(self.db, self.first_order_id, "serial-a", "serial-b")
        self.assertEqual(matched.id, self.first_item.id)

    def test_rejects_serial_from_another_order(self):
        self.assertIsNone(_order_item_for_serial_pair(self.db, self.first_order_id, "SERIAL-X", "SERIAL-Y"))

    def test_rejects_second_serial_from_another_order(self):
        self.assertIsNone(_order_item_for_serial_pair(self.db, self.first_order_id, "SERIAL-A", "SERIAL-Y"))

    def test_accepts_serials_from_different_rows_of_same_order(self):
        matched = _order_item_for_serial_pair(self.db, self.first_order_id, "SERIAL-A", "SERIAL-D")
        self.assertEqual(matched.id, self.first_item.id)


if __name__ == "__main__":
    unittest.main()
