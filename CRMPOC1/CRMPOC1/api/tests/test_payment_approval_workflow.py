from __future__ import annotations

import unittest
import sys
from pathlib import Path
from types import SimpleNamespace

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.config import settings
from app.services.payment_approval_workflow import (
    approval_stage_payload,
    ensure_current_stage_approver,
    is_final_stage,
    next_stage,
    payment_approval_stages,
    user_can_approve_stage,
)


class PaymentApprovalWorkflowTests(unittest.TestCase):
    def setUp(self):
        self.original_steps = settings.payment_approval_steps

    def tearDown(self):
        settings.payment_approval_steps = self.original_steps

    def test_three_step_flow_requires_service_role_manager_then_admin(self):
        settings.payment_approval_steps = 3

        stages = payment_approval_stages()

        self.assertEqual([stage.key for stage in stages], ["service_role", "service_manager", "admin"])
        self.assertFalse(is_final_stage("service_role"))
        self.assertEqual(next_stage("service_role").key, "service_manager")
        self.assertFalse(is_final_stage("service_manager"))
        self.assertEqual(next_stage("service_manager").key, "admin")
        self.assertTrue(is_final_stage("admin"))

        self.assertTrue(user_can_approve_stage(SimpleNamespace(role="service"), "service_role"))
        self.assertFalse(user_can_approve_stage(SimpleNamespace(role="service"), "service_manager"))
        self.assertTrue(user_can_approve_stage(SimpleNamespace(role="service_manager"), "service_manager"))
        self.assertFalse(user_can_approve_stage(SimpleNamespace(role="service_manager"), "admin"))
        self.assertTrue(user_can_approve_stage(SimpleNamespace(role="admin"), "admin"))
        self.assertTrue(user_can_approve_stage(SimpleNamespace(role="admin"), "service_role"))
        self.assertTrue(user_can_approve_stage(SimpleNamespace(role="admin"), "service_manager"))

    def test_two_step_flow_skips_service_manager(self):
        settings.payment_approval_steps = 2

        stages = payment_approval_stages()
        service_payload = approval_stage_payload("service_role")
        admin_payload = approval_stage_payload("admin")

        self.assertEqual([stage.key for stage in stages], ["service_role", "admin"])
        self.assertEqual(next_stage("service_role").key, "admin")
        self.assertFalse(is_final_stage("service_role"))
        self.assertTrue(is_final_stage("admin"))
        self.assertEqual(service_payload["payment_approval_total_steps"], 2)
        self.assertEqual(admin_payload["payment_approval_step"], 2)

    def test_wrong_role_is_rejected_for_current_stage(self):
        settings.payment_approval_steps = 3

        with self.assertRaises(Exception):
            ensure_current_stage_approver(SimpleNamespace(role="service"), "admin")


if __name__ == "__main__":
    unittest.main()
