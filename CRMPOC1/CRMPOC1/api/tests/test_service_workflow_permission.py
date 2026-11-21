import unittest
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

from fastapi import BackgroundTasks, HTTPException
from app.services.permissions import can_manage_service_workflow
from app.routers.services import update_service_status, delete_service


class ServiceWorkflowPermissionTests(unittest.TestCase):
    def test_role_and_permission_are_both_required(self):
        for role in ("admin", "service_manager", "service", "indcool_service", "sub_admin", "incool", "engineer"):
            for granted in (True, False):
                with self.subTest(role=role, granted=granted):
                    with patch("app.services.permissions.can_act_on", return_value=granted):
                        self.assertEqual(can_manage_service_workflow(MagicMock(), SimpleNamespace(role=role), "can_edit"),
                                         granted and role in {"admin", "service_manager"})

    def test_view_is_required_in_addition_to_action(self):
        with patch("app.services.permissions.can_act_on", side_effect=[False]):
            self.assertFalse(can_manage_service_workflow(MagicMock(), SimpleNamespace(role="admin"), "can_edit"))
        with patch("app.services.permissions.can_act_on", side_effect=[True, False]):
            self.assertFalse(can_manage_service_workflow(MagicMock(), SimpleNamespace(role="service_manager"), "can_delete"))

    def test_denied_update_and_delete_do_not_change_records(self):
        for role in ("service", "indcool_service", "service_manager", "admin"):
            with self.subTest(role=role):
                db = MagicMock()
                service = SimpleNamespace(status="Service Team Review")
                user = SimpleNamespace(role=role)
                with patch("app.routers.services._load_visible_service", return_value=service), patch("app.routers.services.can_manage_service_workflow", return_value=False):
                    with self.assertRaises(HTTPException) as error:
                        update_service_status(1, BackgroundTasks(), new_status="Service Completed", remarks=None, db=db, user=user)
                    self.assertEqual(error.exception.status_code, 403)
                    with self.assertRaises(HTTPException) as error:
                        delete_service(1, db=db, user=user)
                    self.assertEqual(error.exception.status_code, 403)
                self.assertEqual(service.status, "Service Team Review")
                db.commit.assert_not_called()


if __name__ == "__main__":
    unittest.main()
