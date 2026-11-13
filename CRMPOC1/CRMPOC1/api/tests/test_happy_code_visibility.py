"""Happy codes are readable only by Admin; engineer validation still works."""
import unittest
from datetime import datetime, timezone
from types import SimpleNamespace
from unittest.mock import MagicMock

from app.models.service import ServiceCompletion
from app.routers.services import _completion_out
from app.services.role_access import can_view_happy_code
from app.services.service_completion_code import validate_engineer_completion_code


class HappyCodeVisibilityTests(unittest.TestCase):
    def test_only_admin_can_read_codes(self):
        for role in ("admin", " Admin ", "service_manager", "sub_admin", "service",
                     "indcool_service", "incool", "engineer", "vendor", "accounts", "audit", ""):
            with self.subTest(role=role):
                self.assertEqual(can_view_happy_code(SimpleNamespace(role=role)),
                                 role.strip().lower() == "admin")
        self.assertFalse(can_view_happy_code(None))

    def test_completion_response_hides_code_from_non_admin(self):
        row = ServiceCompletion(id=1, performed_by_type="engineer",
                                engineer_completion_code="123456",
                                completed_at=datetime.now(timezone.utc))
        for role in ("admin", "service_manager", "sub_admin", "engineer", "incool"):
            with self.subTest(role=role):
                result = _completion_out(MagicMock(), row, user=SimpleNamespace(role=role))
                self.assertEqual(result.engineer_completion_code,
                                 "123456" if role == "admin" else None)
        self.assertIsNone(_completion_out(MagicMock(), row).engineer_completion_code)

    def test_engineer_can_still_submit_customer_code(self):
        service = SimpleNamespace(completion_code="123456")
        self.assertEqual(validate_engineer_completion_code(service, "123456"), "123456")
        with self.assertRaises(ValueError):
            validate_engineer_completion_code(service, "000000")


if __name__ == "__main__":
    unittest.main()
