"""Business logic for Parts: the catalogue, the unified request/approval queue, its timeline, the discuss-link into
Queries, and the warranty-swap log. Nothing here is a route; routes call these and handle HTTP concerns."""

from __future__ import annotations

from datetime import date, datetime, timezone

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models.user import User
from app.models.user_query import UserQuery, UserQueryMember, UserQueryMessage
from app.parts.models import ItemRequest, ItemRequestEvent, ItemRequestPhoto, SparePart
from app.parts.rules import effective_required_photos, next_stage_on_approve, required_photos
from app.services import queries_service as qs


def now() -> datetime:
    return datetime.now(timezone.utc)


# ---------------------------------------------------------------- requests

def next_request_no(pdb: Session) -> str:
    n = pdb.scalar(select(func.max(ItemRequest.id))) or 0
    while True:
        candidate = f"PRQ-{n + 1:05d}"
        if not pdb.scalar(select(ItemRequest.id).where(ItemRequest.request_no == candidate)):
            return candidate
        n += 1


def log(pdb: Session, req: ItemRequest, kind: str, text: str, user: User | None = None) -> None:
    pdb.add(ItemRequestEvent(
        item_request_id=req.id, kind=kind, text=text,
        crm_by_user_id=user.id if user else None, crm_by_name=user.name if user else None,
    ))


def create_request(
    pdb: Session, *, kind: str, description: str, user: User,
    crm_service_request_id: int | None = None, crm_service_request_no: str | None = None,
    crm_installation_request_id: int | None = None, crm_installation_request_no: str | None = None,
    crm_item_code: str | None = None, crm_item_name_cache: str | None = None, crm_serial_no: str | None = None,
    spare_part_id: int | None = None, part_name_cache: str | None = None, amount=None,
    required_photos_override: int | None = None,
) -> ItemRequest:
    req = ItemRequest(
        request_no=next_request_no(pdb), kind=kind, description=description, stage="svm",
        crm_service_request_id=crm_service_request_id, crm_service_request_no=crm_service_request_no,
        crm_installation_request_id=crm_installation_request_id, crm_installation_request_no=crm_installation_request_no,
        crm_item_code=crm_item_code, crm_item_name_cache=crm_item_name_cache, crm_serial_no=crm_serial_no,
        spare_part_id=spare_part_id, part_name_cache=part_name_cache, amount=amount,
        required_photos_override=required_photos_override,
        crm_raised_by_user_id=user.id, crm_raised_by_name=user.name, crm_raised_by_role=user.role,
    )
    pdb.add(req)
    pdb.flush()
    log(pdb, req, "raised", f"Request raised by {user.name}", user)
    return req


def photo_count(pdb: Session, req: ItemRequest) -> int:
    return pdb.scalar(select(func.count()).select_from(ItemRequestPhoto).where(ItemRequestPhoto.item_request_id == req.id)) or 0


def add_photo(pdb: Session, req: ItemRequest, *, file_path: str, label: str | None, user: User) -> ItemRequestPhoto:
    photo = ItemRequestPhoto(item_request_id=req.id, file_path=file_path, label=label, uploaded_by_user_id=user.id)
    pdb.add(photo)
    pdb.flush()
    return photo


class NotReady(Exception):
    pass


class WrongStage(Exception):
    pass


def approve(pdb: Session, req: ItemRequest, *, user: User) -> ItemRequest:
    if req.stage not in ("svm", "sub"):
        raise WrongStage(f"This request is already {req.stage}")
    need = effective_required_photos(req)
    if need and photo_count(pdb, req) < need:
        raise NotReady(f"This request needs {need} photos before it can be approved; it has {photo_count(pdb, req)}")
    from_stage = req.stage
    req.stage = next_stage_on_approve(req.kind, req.amount, req.stage)
    if req.stage == "done":
        req.decided_at = now()
        req.decided_by_user_id = user.id
        req.decided_by_name = user.name
    text = f"Approved by {user.name}" + (" (forwarded to Admin/Sub Admin)" if req.stage == "sub" else "")
    log(pdb, req, "approved", text, user)
    return req


def reject(pdb: Session, req: ItemRequest, *, user: User, reason: str) -> ItemRequest:
    if req.stage not in ("svm", "sub"):
        raise WrongStage(f"This request is already {req.stage}")
    req.stage = "rejected"
    req.decided_at = now()
    req.decided_by_user_id = user.id
    req.decided_by_name = user.name
    log(pdb, req, "rejected", f"Rejected by {user.name}: {reason}", user)
    return req


def resubmit(
    pdb: Session, req: ItemRequest, *, user: User,
    description: str | None = None, amount=None,
) -> ItemRequest:
    """A rejected request isn't a dead end -- whoever raised it fixes what the rejection reason pointed at
    and sends it back through the same chain, under the same request_no, instead of starting over from
    scratch with no link to what came before."""
    if req.stage != "rejected":
        raise WrongStage(f"Only a rejected request can be resubmitted (this one is {req.stage})")
    if description:
        req.description = description
    if amount is not None:
        req.amount = amount
    req.stage = "svm"
    req.decided_at = None
    req.decided_by_user_id = None
    req.decided_by_name = None
    log(pdb, req, "resubmitted", f"Resubmitted by {user.name}", user)
    return req


def mark_supplied(pdb: Session, req: ItemRequest, *, user: User, note: str | None) -> ItemRequest:
    if req.stage != "done":
        raise WrongStage("Only an approved request can be marked supplied")
    log(pdb, req, "supplied", f"Supplied, confirmed by {user.name}" + (f": {note}" if note else ""), user)
    return req


# ---------------------------------------------------------------- discuss (link into Queries, the CRM database)

def open_discuss(db: Session, pdb: Session, req: ItemRequest, *, opener: User, message: str) -> UserQuery:
    """Start a Queries thread about this request, between the engineer who raised it and whoever is asking.
    Both are explicit members regardless of role, so the thread is visible to each of them."""
    if req.crm_query_id:
        raise ValueError("A discussion is already open on this request")
    stamp = now()
    owner_id = req.crm_raised_by_user_id
    q = UserQuery(
        subject=f"About {req.request_no}: {req.description[:120]}", category="Parts", related_to=req.request_no,
        status="Open" if owner_id == opener.id else "Answered",
        owner_id=owner_id, created_by=opener.id, last_message_at=stamp,
        awaiting_since=stamp if owner_id == opener.id else None,
    )
    db.add(q)
    db.flush()
    db.add(UserQueryMember(query_id=q.id, user_id=owner_id, kind="owner", share_history=True, joined_at=stamp))
    if opener.id != owner_id:
        db.add(UserQueryMember(query_id=q.id, user_id=opener.id, kind="member", share_history=True, joined_at=stamp))
    db.add(UserQueryMessage(query_id=q.id, sender_id=opener.id, body=message, created_at=stamp))
    qs.log_event(db, q, "start", f"Opened from {req.request_no} by {opener.name}", opener)
    db.flush()

    req.crm_query_id = q.id
    log(pdb, req, "discuss_opened", f"{opener.name} asked a question (see Queries)", opener)
    return q


# ---------------------------------------------------------------- catalogue

def visible_parts_for_item(pdb: Session, crm_item_code: str, *, engineers_only: bool):
    from app.parts.models import SparePartFitment

    stmt = (
        select(SparePart)
        .join(SparePartFitment, SparePartFitment.spare_part_id == SparePart.id)
        .where(SparePartFitment.crm_item_code == crm_item_code, SparePart.is_active.is_(True))
    )
    if engineers_only:
        stmt = stmt.where(SparePart.engineer_visible.is_(True))
    return pdb.scalars(stmt.order_by(SparePart.part_name)).all()
