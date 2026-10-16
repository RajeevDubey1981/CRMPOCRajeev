"""Assignment scope shared by complaint lists, details, and dashboards."""
from sqlalchemy import or_, select

from app.models.complaint import Complaint
from app.models.installation import InstallationRequest
from app.models.service import ServiceRequest
from app.services.service_access import is_service_desk_user


def apply_complaint_assignment_scope(stmt, user):
    if not is_service_desk_user(user):
        return stmt
    return stmt.where(or_(
        Complaint.id.in_(select(ServiceRequest.complaint_id).where(
            ServiceRequest.deleted_at.is_(None),
            ServiceRequest.complaint_id.isnot(None),
            ServiceRequest.assigned_service_user_id == user.id,
        )),
        Complaint.id.in_(select(InstallationRequest.complaint_id).where(
            InstallationRequest.deleted_at.is_(None),
            InstallationRequest.complaint_id.isnot(None),
            InstallationRequest.assigned_service_user_id == user.id,
        )),
    ))
