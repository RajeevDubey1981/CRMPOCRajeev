"""Run engineer workflows with Non GST accounts against an isolated SQLite database."""
from datetime import date
from sqlalchemy import select
from tests.test_field_photos import FieldPhotoTests as _FieldPhotoTests
from app.models import Complaint, OrderItem, ServiceRequest, User
from app.services.engineer_assignment import get_engineer_assignment_options
from app.services.pending_action_service import get_users_by_roles
from app.services.role_access import ENGINEER_ROLE_NAMES, permission_role_name, role_key
from app.services.permissions import sub_module_scope


class EngineerNonGstFlowTests(_FieldPhotoTests):
    def setUp(self):
        super().setUp()
        self.eng1.role = "Engineer Non GST"
        self.eng2.role = "engineer_non_gst"
        self.db.commit()

    def test_login_and_permissions_match_engineer(self):
        r = self.client.post("/api/auth/login", json={"email": self.eng1.email, "password": "pw123456"})
        self.assertEqual(r.status_code, 200, r.text)
        non_gst = r.json()["user"]
        self.assertEqual(non_gst["role"], "Engineer Non GST")
        self.eng1.role = "engineer"
        self.db.commit()
        regular = self.client.get("/api/auth/me", headers=self.h(self.eng1))
        self.assertEqual(non_gst["permissions"], regular.json()["permissions"])
        for name in ENGINEER_ROLE_NAMES:
            self.assertEqual(role_key(name.upper()), "engineer")
            self.assertEqual(permission_role_name(name), "engineer")

    def test_assignment_options_and_notification_recipients_include_both_types(self):
        regular = self._user("regular@t.com", "engineer")
        self.db.commit()
        expected = {self.eng1.id, self.eng2.id, regular.id}
        options = get_engineer_assignment_options(self.db)
        self.assertEqual({row.id for row in options}, expected)
        self.assertEqual({row.id for row in get_users_by_roles(self.db, {"engineer"})}, expected)
        r = self.client.get("/api/services/lookup/engineers", headers=self.h(self.admin))
        self.assertEqual(r.status_code, 200, r.text)
        self.assertEqual({row["id"] for row in r.json()}, expected)

    def test_observation_approval_and_completion_flow(self):
        from unittest.mock import patch
        from tests.test_field_photos import JPEG
        self.db.get(OrderItem, self.unit.order_item_id).serial_no = "SER-001"
        self.db.commit()
        self.test_engineer_cannot_verify_a_serial_without_a_photo()
        sid = self.unit.service_request_id
        r = self.client.post(f"/api/services/{sid}/serial-verification-review", json={"unit_id": self.unit.id, "decision": "Approve"}, headers=self.h(self.admin))
        self.assertEqual(r.status_code, 200, r.text)
        body = {"unit_id": self.unit.id, "problem_found": "Fan issue", "observation": "Replace fan"}
        r = self.client.post(f"/api/services/{sid}/observations", json=body, headers=self.h(self.eng1))
        self.assertEqual(r.status_code, 200, r.text)
        body["observation"] = "Updated observation"
        r = self.client.post(f"/api/services/{sid}/observations", json=body, headers=self.h(self.eng1))
        self.assertEqual(r.status_code, 200, r.text)
        with patch("app.routers.services.after_service_status_change"), patch("app.routers.services.after_service_approval"):
            r = self.client.post(f"/api/services/{sid}/approval", json={"unit_id": self.unit.id, "decision": "Approve"}, headers=self.h(self.eng1))
            self.assertEqual(r.status_code, 403, r.text)
            r = self.client.post(f"/api/services/{sid}/approval", json={"unit_id": self.unit.id, "decision": "Approve"}, headers=self.h(self.admin))
            self.assertEqual(r.status_code, 200, r.text)
            self.db.expire_all()
            service = self.db.get(ServiceRequest, sid)
            service.completion_code = "123456"
            self.db.commit()
            r = self.client.post(f"/api/services/{sid}/completion", data={"unit_id": self.unit.id, "work_performed": "Replaced fan", "completion_code": "123456"}, files={"proof_document": ("proof.jpg", JPEG, "image/jpeg")}, headers=self.h(self.eng1))
            self.assertEqual(r.status_code, 200, r.text)
            self.assertEqual(r.json()["status"], "Completion Pending Approval")

    def test_lists_and_dashboard_are_identical_and_assignment_scoped(self):
        own = Complaint(comp_no="OWN", customer_name="Own", customer_mobile="1", query_type="Service", assigned_engineer=self.eng1.id)
        other = Complaint(comp_no="OTHER", customer_name="Other", customer_mobile="2", query_type="Service", assigned_engineer=self.eng2.id)
        self.db.add_all([own, other])
        self.db.add(ServiceRequest(request_no="OTHER", customer_name="Other", customer_mobile="2", assigned_engineer_id=self.eng2.id))
        self.db.commit()
        paths = ["/api/complaints", "/api/services", "/api/installations", "/api/dashboard/complaints-summary", "/api/dashboard/installation-summary", "/api/dashboard/services-summary", "/api/dashboard/complaint-chart"]
        expected = {}
        for path in paths:
            r = self.client.get(path, headers=self.h(self.eng1))
            self.assertEqual(r.status_code, 200, (path, r.text))
            expected[path] = r.json()
        self.assertEqual({row["id"] for row in expected["/api/complaints"]["items"]}, {own.id})
        self.assertEqual({row["id"] for row in expected["/api/services"]["items"]}, {self.unit.service_request_id})
        self.eng1.role = "engineer"
        self.db.commit()
        for path in paths:
            r = self.client.get(path, headers=self.h(self.eng1))
            self.assertEqual(r.status_code, 200, (path, r.text))
            self.assertEqual(r.json(), expected[path], path)


# Only the subclass is collected from this module.
del _FieldPhotoTests
