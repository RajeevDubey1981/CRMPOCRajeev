"""Workflow rank and admin-reset behavior (no database)."""
from __future__ import annotations

import unittest
from types import SimpleNamespace
from unittest.mock import MagicMock

from app.services.service_documents import (
    reset_service_workflow_from_status,
    service_workflow_is_revert,
    service_workflow_rank,
)


def _mock_db_with_units(units: list) -> MagicMock:
    db = MagicMock()
    calls = {"n": 0}

    def scalars(_stmt):
        calls["n"] += 1
        result = MagicMock()
        result.all.return_value = []
        # Four engineer-record deletes, then unit serial clear.
        if calls["n"] >= 5:
            result.__iter__ = lambda self: iter(units)
        else:
            result.__iter__ = lambda self: iter([])
        return result

    db.scalars.side_effect = scalars
    return db


class ServiceWorkflowResetTests(unittest.TestCase):
    def test_workflow_rank_order(self):
        self.assertLess(service_workflow_rank("Assigned"), service_workflow_rank("Serial Verified"))
        self.assertLess(
            service_workflow_rank("Serial Verified"),
            service_workflow_rank("Pending Service Approval"),
        )
        self.assertTrue(service_workflow_is_revert("Payment Completed", "Assigned"))
        self.assertFalse(service_workflow_is_revert("Assigned", "Serial Verified"))

    def test_reset_to_assigned_clears_serial(self):
        service = SimpleNamespace(
            id=99,
            serial_no="IDCACEZO26072901223",
            order_item_id=12,
            warranty_status="IN WARRANTY",
            approved_at=None,
            completed_at=None,
            closed_at=None,
            completion_code="1234",
            status_date=None,
        )
        unit = SimpleNamespace(
            service_request_id=99,
            serial_verified_at="2020-01-01",
            warranty_status="IN WARRANTY",
            service_type="Warranty Service",
        )
        db = _mock_db_with_units([unit])

        reset_service_workflow_from_status(db, service, "Assigned")

        self.assertIsNone(service.serial_no)
        self.assertIsNone(service.order_item_id)
        self.assertIsNone(service.warranty_status)
        self.assertIsNone(unit.serial_verified_at)
        self.assertIsNone(service.approved_at)
        self.assertIsNone(service.completed_at)
        self.assertIsNone(service.completion_code)

    def test_reset_to_serial_verified_keeps_serial(self):
        service = SimpleNamespace(
            id=1,
            serial_no="SERIAL1",
            order_item_id=3,
            warranty_status="IN WARRANTY",
            approved_at="2020-01-01",
            completed_at=None,
            closed_at=None,
            completion_code=None,
            status_date=None,
        )
        db = _mock_db_with_units([])

        reset_service_workflow_from_status(db, service, "Serial Verified")

        self.assertEqual(service.serial_no, "SERIAL1")
        self.assertIsNone(service.approved_at)


if __name__ == "__main__":
    unittest.main()
