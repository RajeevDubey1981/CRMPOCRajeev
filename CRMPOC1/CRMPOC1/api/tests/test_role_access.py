import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.services.role_access import permission_role_name


class PermissionRoleNameTests(unittest.TestCase):
    def test_sub_admin_uses_its_own_role_card(self):
        self.assertEqual(permission_role_name("sub_admin"), "sub_admin")
        self.assertEqual(permission_role_name(" Sub_Admin "), "sub_admin")

    def test_indcool_aliases_share_indcool_service(self):
        for role in ("indcool", "Indcool Service"):
            self.assertEqual(permission_role_name(role), "indcool_service")

    def test_service_roles_keep_their_own_permission_card(self):
        for role in ("service", "service_manager"):
            self.assertEqual(permission_role_name(role), role)

    def test_other_roles_keep_their_own_name(self):
        for role in ("admin", "vendor", "engineer", "sales", "callcenter"):
            self.assertEqual(permission_role_name(role), role)


if __name__ == "__main__":
    unittest.main()
