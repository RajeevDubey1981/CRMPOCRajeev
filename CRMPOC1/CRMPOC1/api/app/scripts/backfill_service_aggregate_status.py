"""One-time backfill: re-derive each unit-workflow service request's own status from its serials'
current statuses, fixing requests whose overall status went stale because raising payment for a
single serial never used to re-sync the parent (see services.py's raise-payment unit_id branch)."""

from app.database import SessionLocal
from app.models.service import ServiceRequest
from app.services.service_unit_workflow import list_work_units, sync_aggregate_service_status


def main() -> None:
    db = SessionLocal()
    try:
        changed = 0
        checked = 0
        for service in db.query(ServiceRequest).filter(ServiceRequest.deleted_at.is_(None)).all():
            if not list_work_units(db, service.id):
                continue
            checked += 1
            before = service.status
            sync_aggregate_service_status(db, service)
            if service.status != before:
                changed += 1
                print(f"Service #{service.id} ({service.request_no}): {before!r} -> {service.status!r}")
        db.commit()
        print(f"[backfill_service_aggregate_status] checked={checked} changed={changed}")
    finally:
        db.close()


if __name__ == "__main__":
    main()
