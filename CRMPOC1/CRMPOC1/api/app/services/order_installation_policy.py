"""Apply the order's optional installation exemption without fabricating engineer work."""
from fastapi import HTTPException
from sqlalchemy import or_, select
from sqlalchemy.orm import Session

from app.models.installation import InstallationRequest
from app.models.order import Order, OrderItem


def sync_order_installation_policy(db: Session, order: Order) -> None:
    db.flush()
    items = db.scalars(select(OrderItem).where(OrderItem.order_id == order.id)).all()
    if not order.installation_required:
        active = db.scalar(select(InstallationRequest.id).where(
            or_(InstallationRequest.order_id == order.id, InstallationRequest.order_item_id.in_([item.id for item in items])),
            InstallationRequest.status.notin_(("Completed", "Rejected")),
        ).limit(1))
        if active is not None:
            raise HTTPException(409, "Cancel existing installation requests before marking this order as installation not required")

    auto_complete = not order.installation_required and order.status in {"Delivered", "Completed"}
    for item in items:
        if auto_complete:
            if item.installation_status != "Completed":
                item.installation_status = "Completed"
                item.installation_auto_completed = True
        elif item.installation_auto_completed:
            # Undo only the automatic exemption; preserve genuinely completed installations.
            item.installation_status = "Not Requested"
            item.installation_auto_completed = False


def require_order_installation(order: Order) -> None:
    if not order.installation_required:
        raise HTTPException(400, "Installation is not required for this order")
