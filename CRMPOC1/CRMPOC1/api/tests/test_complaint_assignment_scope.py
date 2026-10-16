"""Regression coverage for service desk complaint visibility."""
import os
import sys
import unittest
from pathlib import Path
from types import SimpleNamespace

os.environ.setdefault("MYSQL_DATABASE_URL", "sqlite://")
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session
from app.models.complaint import Complaint
from app.models.installation import InstallationRequest
from app.models.service import ServiceRequest
from app.services.complaint_access import apply_complaint_assignment_scope


class ComplaintAssignmentScopeTests(unittest.TestCase):
    def test_only_active_requests_assigned_to_current_desk_user_are_visible(self):
        engine = create_engine("sqlite://")
        # Only the columns used by the scope are needed for this regression.
        with engine.begin() as connection:
            connection.exec_driver_sql("CREATE TABLE complaints (id INTEGER PRIMARY KEY)")
            for table in ("service_requests", "installation_requests"):
                connection.exec_driver_sql(f"CREATE TABLE {table} (complaint_id INTEGER, assigned_service_user_id INTEGER, deleted_at DATETIME)")
            connection.exec_driver_sql("INSERT INTO complaints VALUES (1), (2), (3), (4), (5)")
            connection.exec_driver_sql("INSERT INTO service_requests VALUES (1, 10, NULL), (2, 20, NULL), (3, NULL, NULL), (4, 10, '2026-10-16')")
            connection.exec_driver_sql("INSERT INTO installation_requests VALUES (5, 10, NULL)")
        with Session(engine) as db:
            for role in ("service", "indcool_service"):
                stmt = apply_complaint_assignment_scope(select(Complaint.id), SimpleNamespace(id=10, role=role))
                self.assertEqual(set(db.scalars(stmt)), {1, 5})
            stmt = apply_complaint_assignment_scope(select(Complaint.id), SimpleNamespace(id=20, role="service"))
            self.assertEqual(set(db.scalars(stmt)), {2})
            for role in ("admin", "service_manager"):
                stmt = apply_complaint_assignment_scope(select(Complaint.id), SimpleNamespace(id=10, role=role))
                self.assertEqual(set(db.scalars(stmt)), {1, 2, 3, 4, 5})
        engine.dispose()


if __name__ == "__main__":
    unittest.main()
