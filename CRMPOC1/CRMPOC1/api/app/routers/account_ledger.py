"""The vendor/engineer Dr-Cr ledger. Two party types share one table (AccountLedgerEntry) and one
balance/overdue calculation; everything else here is just which party type a call is about.

Permissions: "vendor_ledger" and "engineer_ledger" are ordinary permission modules (Admin -> Roles),
can_view for read-only access, can_edit for setting an opening balance/payment cycle or adding an entry.
"""

from __future__ import annotations

from datetime import date, datetime, timedelta, timezone
from decimal import Decimal
from typing import Literal, Optional

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Query, UploadFile, status
from pydantic import BaseModel, Field
from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session

from app.database import get_db
from app.deps import get_current_user
from app.models.account_ledger import AccountLedgerEntry
from app.models.bank_statement import BankStatementImport, BankStatementLine
from app.models.order import Order, OrderItem
from app.models.pending_ledger_payment import PendingLedgerPayment
from app.models.user import User
from app.models.vendor import Vendor
from app.models.vendor_expense_approval import VendorExpenseApproval
from app.services.account_ledger import compute_balance, compute_oldest_unpaid_since, compute_overdue_days
from app.services.bank_statement_matching import match_description
from app.services.bank_statement_parser import parse_csv
from app.services.email_service import send_email
from app.services.file_service import persist_upload, validate_upload
from app.services.permissions import can_act_on
from app.services.role_access import is_service_team, is_system_admin, role_key

router = APIRouter(prefix="/api/ledger", tags=["account-ledger"])

PartyType = Literal["vendor", "engineer"]
MODULE_FOR = {"vendor": "vendor_ledger", "engineer": "engineer_ledger"}


def _require(db: Session, user: User, party_type: PartyType, flag: str) -> None:
    if not can_act_on(db, user, MODULE_FOR[party_type], flag, None):
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Your role cannot do this")


def _load_party(db: Session, party_type: PartyType, party_id: int):
    if party_type == "vendor":
        party = db.get(Vendor, party_id)
        if party is None or party.deleted_at is not None:
            raise HTTPException(status.HTTP_404_NOT_FOUND, "Vendor not found")
    else:
        party = db.get(User, party_id)
        if party is None or party.deleted_at is not None or role_key(party.role) != "engineer":
            raise HTTPException(status.HTTP_404_NOT_FOUND, "Engineer not found")
    return party


def _party_name(party, party_type: PartyType) -> str:
    return party.name_of_firm if party_type == "vendor" else party.name


def _party_name_safe(db: Session, party_type: str, party_id: int) -> str | None:
    if party_type == "vendor":
        v = db.get(Vendor, party_id)
        return v.name_of_firm if v else None
    u = db.get(User, party_id)
    return u.name if u else None


def _create_pending_payment(
    db: Session, *, party_type: str, party_id: int, amount: float, description: str,
    source_type: str, source_id: int | None, entry_date: date, raised_by_user_id: int,
) -> PendingLedgerPayment:
    """A debit Accounts/Accounts Manager just generated, held for Audit instead of posted straight away.
    Admin bypasses this (see is_system_admin checks at each call site) and still posts directly."""
    pending = PendingLedgerPayment(
        party_type=party_type, party_id=party_id, amount=amount, description=description,
        source_type=source_type, source_id=source_id, entry_date=entry_date,
        raised_by_user_id=raised_by_user_id, status="Pending",
    )
    db.add(pending)
    db.flush()
    return pending


def _post_pending_payment(db: Session, pending: PendingLedgerPayment) -> AccountLedgerEntry:
    """Audit approved it: write the real ledger debit now, and sync back to whatever raised it."""
    entry = AccountLedgerEntry(
        party_type=pending.party_type, party_id=pending.party_id, entry_type="debit", amount=pending.amount,
        description=pending.description, source_type=pending.source_type, source_id=pending.source_id,
        entry_date=pending.entry_date, created_by_user_id=pending.raised_by_user_id,
    )
    entry.pending_payment_id = pending.id
    db.add(entry)
    db.flush()
    pending.posted_entry_id = entry.id
    if pending.source_type == "bank_statement" and pending.source_id:
        line = db.get(BankStatementLine, pending.source_id)
        if line is not None and line.pending_payment_id == pending.id:
            line.status = "posted"
            line.ledger_entry_id = entry.id
    return entry


def _pending_payment_out(db: Session, p: PendingLedgerPayment) -> dict:
    raiser = db.get(User, p.raised_by_user_id) if p.raised_by_user_id else None
    decider = db.get(User, p.decided_by_user_id) if p.decided_by_user_id else None
    return {
        "id": p.id, "party_type": p.party_type, "party_id": p.party_id,
        "party_name": _party_name_safe(db, p.party_type, p.party_id),
        "amount": float(p.amount), "description": p.description,
        "source_type": p.source_type, "source_id": p.source_id, "entry_date": p.entry_date,
        "raised_by_name": raiser.name if raiser else None,
        "status": p.status,
        "decided_by_name": decider.name if decider else None,
        "decided_at": p.decided_at, "decision_note": p.decision_note,
        "created_at": p.created_at,
    }


def _payment_status_for(db: Session, source_type: str, source_id: int) -> str | None:
    """Whether a would-be debit from this source has actually posted. None means either posted directly
    (Admin bypassed Audit) or no payment was ever raised for it."""
    pending = db.scalar(
        select(PendingLedgerPayment)
        .where(PendingLedgerPayment.source_type == source_type, PendingLedgerPayment.source_id == source_id)
        .order_by(PendingLedgerPayment.id.desc())
    )
    if pending is None:
        return None
    if pending.status == "Pending":
        return "Pending audit"
    if pending.status == "Approved":
        return "Posted"
    return "Rejected by audit"


def _entries(db: Session, party_type: PartyType, party_id: int) -> list[AccountLedgerEntry]:
    return list(db.scalars(
        select(AccountLedgerEntry)
        .where(AccountLedgerEntry.party_type == party_type, AccountLedgerEntry.party_id == party_id)
        .order_by(AccountLedgerEntry.entry_date, AccountLedgerEntry.id)
    ).all())


def _entry_out(e: AccountLedgerEntry) -> dict:
    return {
        "id": e.id, "entry_date": e.entry_date, "entry_type": e.entry_type,
        "amount": float(e.amount), "description": e.description,
        "source_type": e.source_type, "source_id": e.source_id,
        "audited": bool(e.pending_payment_id), "audit_bypassed": bool(e.audit_bypassed),
    }


def _detail(db: Session, party_type: PartyType, party_id: int, party, can_edit: bool) -> dict:
    entries = _entries(db, party_type, party_id)
    balance = compute_balance(entries)
    oldest_unpaid = compute_oldest_unpaid_since(entries)
    cycle_days = party.payment_cycle_days
    overdue_days = compute_overdue_days(oldest_unpaid, cycle_days)
    opening = next((e for e in entries if e.source_type == "opening"), None)
    bank_details = None
    if party_type == "engineer" and can_edit and bool(party.bank_account_number):
        bank_details = {
            "bank_account_holder_name": party.bank_account_holder_name,
            "bank_name": party.bank_name,
            "bank_account_number": party.bank_account_number,
            "bank_ifsc": party.bank_ifsc,
            "bank_branch": party.bank_branch,
        }
    return {
        "party_type": party_type, "party_id": party_id, "name": _party_name(party, party_type),
        "payment_cycle_days": cycle_days,
        "opening_balance": float(opening.amount) if opening else None,
        "opening_balance_type": opening.entry_type if opening else None,
        "balance": float(balance),
        "total_credit": float(sum((Decimal(str(e.amount)) for e in entries if e.entry_type == "credit"), Decimal("0"))),
        "total_debit": float(sum((Decimal(str(e.amount)) for e in entries if e.entry_type == "debit"), Decimal("0"))),
        "oldest_unpaid_since": oldest_unpaid,
        "overdue_days": overdue_days,
        "can_edit": can_edit,
        "bank_details": bank_details,
        "has_bank_details": bool(party.bank_account_number) if party_type == "engineer" else None,
        "entries": [_entry_out(e) for e in entries],
        "pending_payments": [
            _pending_payment_out(db, p) for p in db.scalars(
                select(PendingLedgerPayment)
                .where(
                    PendingLedgerPayment.party_type == party_type,
                    PendingLedgerPayment.party_id == party_id,
                    PendingLedgerPayment.status == "Pending",
                )
                .order_by(PendingLedgerPayment.created_at.desc())
            )
        ] if can_edit else [],
    }


def _can_coordinate_with_vendor(db: Session, user: User) -> bool:
    """Who may confirm a return's material receipt or raise a vendor-approval expense: Sales, Service,
    Accounts, or any internal role with at least view access to Orders -- never the vendor or engineer
    accounts themselves, since the whole point is that the VENDOR is the one being asked. Orders
    can_edit is too narrow here: Sales typically only has can_view on Orders in this CRM."""
    if role_key(user.role) in ("vendor", "engineer"):
        return False
    return can_act_on(db, user, "orders", "can_view", None)


def _order_unit_count(db: Session, order_id: int) -> int:
    total = db.scalar(select(func.sum(OrderItem.item_qty)).where(OrderItem.order_id == order_id))
    return int(total) if total else 1


def _return_pending_out(db: Session, order: Order) -> dict:
    vendor = db.get(Vendor, order.vendor_id) if order.vendor_id else None
    confirmer = db.get(User, order.material_receipt_confirmed_by_user_id) if order.material_receipt_confirmed_by_user_id else None
    return {
        "order_id": order.id, "order_no": order.order_no, "status": order.status,
        "vendor_id": order.vendor_id, "vendor_name": vendor.name_of_firm if vendor else None,
        "customer_name": order.customer_name,
        "oem_bill_amount": float(order.oem_bill_amount) if order.oem_bill_amount is not None else None,
        "unit_count": _order_unit_count(db, order.id),
        "suggested_return_amount": float(order.oem_bill_amount) if order.oem_bill_amount is not None else None,
        "material_receipt_confirmed_at": order.material_receipt_confirmed_at,
        "material_receipt_confirmed_by": confirmer.name if confirmer else None,
    }


@router.get("/returns/pending")
def list_pending_returns(db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    """The Accounts dashboard's return/cancellation queue: every Returned or Cancelled order not yet
    processed. Nothing here has touched the vendor's ledger -- see process_return below."""
    if not can_act_on(db, user, "vendor_ledger", "can_edit", None):
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Your role cannot view this")
    orders = db.scalars(
        select(Order)
        .where(Order.status.in_(["Returned", "Cancelled"]), Order.accounts_return_processed_at.is_(None), Order.deleted_at.is_(None))
        .order_by(Order.id.desc())
        .limit(200)
    ).all()
    return [_return_pending_out(db, o) for o in orders]


@router.post("/returns/{order_id}/confirm-receipt")
def confirm_material_receipt(order_id: int, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    """Sales or the Service Team tick this once the returned goods are physically back in hand. Accounts
    cannot debit the vendor for a return until this is done."""
    if not _can_coordinate_with_vendor(db, user):
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Your role cannot do this")
    order = db.get(Order, order_id)
    if order is None or order.deleted_at is not None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Order not found")
    if order.status not in ("Returned", "Cancelled"):
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Order is not Returned or Cancelled")
    order.material_receipt_confirmed_by_user_id = user.id
    order.material_receipt_confirmed_at = datetime.now(timezone.utc)
    db.commit()
    return _return_pending_out(db, order)


class ProcessReturnIn(BaseModel):
    return_amount: float = Field(ge=0, default=0)
    return_charges_amount: float = Field(ge=0, default=0)
    note: str = Field(min_length=2)
    entry_date: Optional[date] = None


@router.post("/returns/{order_id}/process")
def process_return(
    order_id: int, body: ProcessReturnIn,
    db: Session = Depends(get_db), user: User = Depends(get_current_user),
):
    """Accounts debits the vendor for a processed return: the return amount and the return/courier
    charges post as two separate debits, never combined into one figure, per how this was designed."""
    if not can_act_on(db, user, "vendor_ledger", "can_edit", None):
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Your role cannot do this")
    order = db.get(Order, order_id)
    if order is None or order.deleted_at is not None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Order not found")
    if order.status not in ("Returned", "Cancelled"):
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Order is not Returned or Cancelled")
    if order.material_receipt_confirmed_at is None:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Material receipt must be confirmed by Sales/Service first")
    if order.accounts_return_processed_at is not None:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "This return has already been processed")
    if order.vendor_id is None:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "This order has no vendor to debit")
    if body.return_amount <= 0 and body.return_charges_amount <= 0:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Enter a return amount or return charges")

    entry_date = body.entry_date or datetime.now(timezone.utc).date()
    ref = order.order_no or str(order.id)
    bypass = is_system_admin(user)

    def _post_or_queue(amount: float, description: str) -> None:
        if bypass:
            db.add(AccountLedgerEntry(
                party_type="vendor", party_id=order.vendor_id, entry_type="debit", amount=amount,
                description=description, source_type="return", source_id=order.id,
                entry_date=entry_date, created_by_user_id=user.id, audit_bypassed=True,
            ))
        else:
            _create_pending_payment(
                db, party_type="vendor", party_id=order.vendor_id, amount=amount, description=description,
                source_type="return", source_id=order.id, entry_date=entry_date, raised_by_user_id=user.id,
            )

    if body.return_amount > 0:
        _post_or_queue(body.return_amount, f"Order {ref} -- return amount. {body.note}")
    if body.return_charges_amount > 0:
        _post_or_queue(body.return_charges_amount, f"Order {ref} -- return/courier charges. {body.note}")
    order.accounts_return_processed_at = datetime.now(timezone.utc)
    db.commit()
    return _return_pending_out(db, order)


def _vendor_expense_out(approval: VendorExpenseApproval, order: Order | None, vendor: Vendor | None, raised_by: User | None = None) -> dict:
    return {
        "id": approval.id, "order_id": approval.order_id, "order_no": order.order_no if order else None,
        "vendor_id": approval.vendor_id, "vendor_name": vendor.name_of_firm if vendor else None,
        "amount": float(approval.amount), "reason": approval.reason, "raised_by_type": approval.raised_by_type,
        "raised_by_name": raised_by.name if raised_by else None,
        "status": approval.status, "created_at": approval.created_at, "decided_at": approval.decided_at,
        "decision_note": approval.decision_note,
    }


class VendorExpenseRaiseIn(BaseModel):
    order_id: int
    amount: float = Field(gt=0)
    reason: str = Field(min_length=3)


@router.post("/vendor-expenses")
def raise_vendor_expense(
    body: VendorExpenseRaiseIn, background_tasks: BackgroundTasks,
    db: Session = Depends(get_db), user: User = Depends(get_current_user),
):
    """Sales or the Service Team raises an extra delivery/installation expense against an order, for
    the order's own vendor to approve on their own portal. Nothing debits until the vendor approves."""
    if not _can_coordinate_with_vendor(db, user):
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Your role cannot raise this")
    order = db.get(Order, body.order_id)
    if order is None or order.deleted_at is not None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Order not found")
    if order.vendor_id is None:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "This order has no vendor")
    vendor = db.get(Vendor, order.vendor_id)
    if vendor is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Vendor not found")

    approval = VendorExpenseApproval(
        order_id=order.id, vendor_id=vendor.id, amount=body.amount, reason=body.reason,
        raised_by_user_id=user.id, raised_by_type="service_team" if is_service_team(user) else "sales",
        status="Pending",
    )
    db.add(approval)
    db.commit()
    db.refresh(approval)

    if vendor.email:
        ref = order.order_no or str(order.id)
        subject = f"Approval needed: extra expense on order {ref}"
        html_body = (
            f"<p>Dear {vendor.name_of_firm},</p>"
            f"<p>INDcool team has raised an extra expense of <b>Rs. {body.amount:,.2f}</b> against your order "
            f"<b>{ref}</b>.</p>"
            f"<p><b>Reason:</b> {body.reason}</p>"
            f"<p>Please sign in to your vendor portal to approve or reject this. Nothing is debited from "
            f"your account until you approve it.</p>"
            f"<p>Regards,<br/>INDcool team</p>"
        )
        text_body = (
            f"INDcool team has raised an extra expense of Rs. {body.amount:,.2f} against order {ref}. "
            f"Reason: {body.reason}. Sign in to your vendor portal to approve or reject it."
        )
        background_tasks.add_task(send_email, vendor.email, subject, html_body, text_body)

    return _vendor_expense_out(approval, order, vendor, user)


@router.get("/vendor-expenses")
def list_vendor_expenses(
    vendor_id: Optional[int] = None, order_id: Optional[int] = None,
    status_filter: Optional[str] = Query(None, alias="status"),
    mine: bool = False,
    db: Session = Depends(get_db), user: User = Depends(get_current_user),
):
    if role_key(user.role) == "vendor":
        own_vendor = db.scalar(select(Vendor).where(Vendor.email == user.email))
        if own_vendor is None:
            return []
        vendor_id = own_vendor.id
    elif mine:
        pass  # "what I raised" needs no module permission beyond being able to raise one in the first place
    elif not (can_act_on(db, user, "vendor_ledger", "can_view", None) or can_act_on(db, user, "orders", "can_view", None)):
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Your role cannot view this")

    stmt = select(VendorExpenseApproval).order_by(VendorExpenseApproval.created_at.desc())
    if mine:
        stmt = stmt.where(VendorExpenseApproval.raised_by_user_id == user.id)
    if vendor_id:
        stmt = stmt.where(VendorExpenseApproval.vendor_id == vendor_id)
    if order_id:
        stmt = stmt.where(VendorExpenseApproval.order_id == order_id)
    if status_filter:
        stmt = stmt.where(VendorExpenseApproval.status == status_filter)
    rows = db.scalars(stmt.limit(200)).all()

    order_ids = {r.order_id for r in rows} or {0}
    vendor_ids = {r.vendor_id for r in rows} or {0}
    raiser_ids = {r.raised_by_user_id for r in rows if r.raised_by_user_id} or {0}
    orders = {o.id: o for o in db.scalars(select(Order).where(Order.id.in_(order_ids)))}
    vendors = {v.id: v for v in db.scalars(select(Vendor).where(Vendor.id.in_(vendor_ids)))}
    raisers = {u.id: u for u in db.scalars(select(User).where(User.id.in_(raiser_ids)))}
    return [
        _vendor_expense_out(r, orders.get(r.order_id), vendors.get(r.vendor_id), raisers.get(r.raised_by_user_id))
        for r in rows
    ]


class VendorExpenseDecideIn(BaseModel):
    decision: Literal["Approved", "Rejected"]
    note: Optional[str] = None


@router.post("/vendor-expenses/{approval_id}/decide")
def decide_vendor_expense(
    approval_id: int, body: VendorExpenseDecideIn,
    db: Session = Depends(get_db), user: User = Depends(get_current_user),
):
    approval = db.get(VendorExpenseApproval, approval_id)
    if approval is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Not found")
    if role_key(user.role) != "vendor":
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Only the vendor can decide this")
    vendor = db.scalar(select(Vendor).where(Vendor.email == user.email))
    if vendor is None or vendor.id != approval.vendor_id:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "This approval is not for your vendor account")
    if approval.status != "Pending":
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "This has already been decided")

    approval.status = body.decision
    approval.decided_at = datetime.now(timezone.utc)
    approval.decision_note = body.note
    order = db.get(Order, approval.order_id)
    if body.decision == "Approved":
        ref = order.order_no if order else approval.order_id
        db.add(AccountLedgerEntry(
            party_type="vendor", party_id=approval.vendor_id, entry_type="debit", amount=approval.amount,
            description=f"Order {ref} -- approved extra expense. {approval.reason}",
            source_type="vendor_approved_expense", source_id=approval.id,
            entry_date=datetime.now(timezone.utc).date(), created_by_user_id=user.id,
        ))
    db.commit()
    raiser = db.get(User, approval.raised_by_user_id) if approval.raised_by_user_id else None
    return _vendor_expense_out(approval, order, vendor, raiser)


def _statement_import_out(imp: BankStatementImport, lines: list[BankStatementLine]) -> dict:
    return {
        "id": imp.id, "file_name": imp.file_name, "created_at": imp.created_at,
        "line_count": len(lines),
        "lines": [_statement_line_out(l) for l in lines],
    }


def _statement_line_out(line: BankStatementLine) -> dict:
    return {
        "id": line.id, "line_date": line.line_date, "description": line.description, "amount": float(line.amount),
        "matched_party_type": line.matched_party_type, "matched_party_id": line.matched_party_id,
        "match_confidence": float(line.match_confidence) if line.match_confidence is not None else None,
        "match_reason": line.match_reason, "status": line.status,
        "pending_payment_id": line.pending_payment_id,
    }


@router.post("/statements/upload")
async def upload_statement(
    file: UploadFile, db: Session = Depends(get_db), user: User = Depends(get_current_user),
):
    """Accounts uploads a bank statement CSV; each row is matched against vendors and engineers by
    phone/code/name and held for review -- nothing posts to a ledger until a line is confirmed."""
    if not (can_act_on(db, user, "vendor_ledger", "can_edit", None) or can_act_on(db, user, "engineer_ledger", "can_edit", None)):
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Your role cannot upload statements")

    extension = validate_upload(
        file,
        allowed_ext={".csv"},
        allowed_mime={"text/csv", "application/vnd.ms-excel", "application/csv", "text/plain", "application/octet-stream"},
    )
    contents = await file.read()
    if len(contents) > 10 * 1024 * 1024:
        raise HTTPException(status.HTTP_413_REQUEST_ENTITY_TOO_LARGE, "File exceeds 10MB limit")
    if not contents:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Empty file")
    try:
        parsed = parse_csv(contents)
    except ValueError as exc:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, str(exc)) from exc
    if not parsed:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "No payout rows found in this file")

    file_path = persist_upload(contents, extension, "bank_statements", reencode_images=False)
    imp = BankStatementImport(uploaded_by_user_id=user.id, file_name=file.filename or "statement.csv", file_path=file_path)
    db.add(imp)
    db.flush()

    lines: list[BankStatementLine] = []
    for p in parsed:
        party_type, party_id, confidence, reason = match_description(db, p.description)
        line = BankStatementLine(
            import_id=imp.id, line_date=p.line_date, description=p.description, amount=p.amount,
            matched_party_type=party_type, matched_party_id=party_id,
            match_confidence=confidence or None, match_reason=reason or None,
            status="matched" if party_type else "unmatched",
        )
        db.add(line)
        lines.append(line)
    db.commit()
    return _statement_import_out(imp, lines)


@router.get("/statements/{import_id}")
def get_statement(import_id: int, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    if not (can_act_on(db, user, "vendor_ledger", "can_edit", None) or can_act_on(db, user, "engineer_ledger", "can_edit", None)):
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Your role cannot view this")
    imp = db.get(BankStatementImport, import_id)
    if imp is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Not found")
    lines = list(db.scalars(select(BankStatementLine).where(BankStatementLine.import_id == import_id).order_by(BankStatementLine.id)))
    return _statement_import_out(imp, lines)


class ConfirmLineIn(BaseModel):
    party_type: PartyType
    party_id: int
    amount: Optional[float] = Field(default=None, gt=0)


@router.post("/statements/{import_id}/lines/{line_id}/confirm")
def confirm_statement_line(
    import_id: int, line_id: int, body: ConfirmLineIn,
    db: Session = Depends(get_db), user: User = Depends(get_current_user),
):
    _require(db, user, body.party_type, "can_edit")
    line = db.scalar(select(BankStatementLine).where(BankStatementLine.id == line_id, BankStatementLine.import_id == import_id))
    if line is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Statement line not found")
    if line.status in ("posted", "pending_audit"):
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "This line has already been posted or submitted for audit")
    party = _load_party(db, body.party_type, body.party_id)
    amount = body.amount if body.amount is not None else float(line.amount)
    description = f"Bank statement: {line.description}"

    line.matched_party_type = body.party_type
    line.matched_party_id = body.party_id
    if is_system_admin(user):
        entry = AccountLedgerEntry(
            party_type=body.party_type, party_id=body.party_id, entry_type="debit", amount=amount,
            description=description, source_type="bank_statement", source_id=line.id,
            entry_date=line.line_date, created_by_user_id=user.id, audit_bypassed=True,
        )
        db.add(entry)
        db.flush()
        line.status = "posted"
        line.ledger_entry_id = entry.id
    else:
        pending = _create_pending_payment(
            db, party_type=body.party_type, party_id=body.party_id, amount=amount, description=description,
            source_type="bank_statement", source_id=line.id, entry_date=line.line_date, raised_by_user_id=user.id,
        )
        line.status = "pending_audit"
        line.pending_payment_id = pending.id
    db.commit()
    return _statement_line_out(line)


@router.post("/statements/{import_id}/lines/{line_id}/ignore")
def ignore_statement_line(import_id: int, line_id: int, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    if not (can_act_on(db, user, "vendor_ledger", "can_edit", None) or can_act_on(db, user, "engineer_ledger", "can_edit", None)):
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Your role cannot do this")
    line = db.scalar(select(BankStatementLine).where(BankStatementLine.id == line_id, BankStatementLine.import_id == import_id))
    if line is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Statement line not found")
    if line.status in ("posted", "pending_audit"):
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "This line has already been posted or submitted for audit")
    line.status = "ignored"
    db.commit()
    return _statement_line_out(line)


@router.get("/audit/pending")
def list_pending_payments(db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    """Audit's queue: every debit Accounts/Accounts Manager generated (a manual entry, a return, a
    confirmed bank statement line) that hasn't posted yet. Admin bypasses this queue entirely -- its
    rows never show up here, they post straight away with audit_bypassed=True on the ledger entry."""
    if not can_act_on(db, user, "ledger_audit", "can_view", None):
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Your role cannot view this")
    rows = db.scalars(
        select(PendingLedgerPayment).where(PendingLedgerPayment.status == "Pending").order_by(PendingLedgerPayment.created_at)
    ).all()
    return [_pending_payment_out(db, p) for p in rows]


class AuditDecideIn(BaseModel):
    ids: list[int] = Field(min_length=1, max_length=200)
    decision: Literal["Approved", "Rejected"]
    note: Optional[str] = None


@router.post("/audit/decide")
def decide_pending_payments(
    body: AuditDecideIn, db: Session = Depends(get_db), user: User = Depends(get_current_user),
):
    """Approve or reject one or several pending payments in one call -- the "batch" option: Audit
    multi-selects a day's worth of items and decides them together."""
    if not can_act_on(db, user, "ledger_audit", "can_edit", None):
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Your role cannot do this")
    if body.decision == "Rejected" and not (body.note or "").strip():
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "A note is required when rejecting")

    rows = db.scalars(select(PendingLedgerPayment).where(PendingLedgerPayment.id.in_(body.ids))).all()
    found = {r.id for r in rows}
    missing = set(body.ids) - found
    if missing:
        raise HTTPException(status.HTTP_404_NOT_FOUND, f"Not found: {sorted(missing)}")
    not_pending = [r.id for r in rows if r.status != "Pending"]
    if not_pending:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, f"Already decided: {sorted(not_pending)}")

    for p in rows:
        p.status = body.decision
        p.decided_by_user_id = user.id
        p.decided_at = datetime.now(timezone.utc)
        p.decision_note = body.note
        if body.decision == "Approved":
            _post_pending_payment(db, p)
        else:
            if p.source_type == "bank_statement" and p.source_id:
                line = db.get(BankStatementLine, p.source_id)
                if line is not None and line.pending_payment_id == p.id:
                    line.status = "matched"  # back to reviewable -- not ignored, Accounts can re-confirm
                    line.pending_payment_id = None
            if p.source_type == "return" and p.source_id:
                order = db.get(Order, p.source_id)
                # Only reopen the order if nothing from this return ever actually posted or is still
                # pending elsewhere -- a partially-approved return (one leg posted) stays "processed".
                still_active = db.scalar(
                    select(func.count()).select_from(PendingLedgerPayment).where(
                        PendingLedgerPayment.source_type == "return", PendingLedgerPayment.source_id == p.source_id,
                        PendingLedgerPayment.status == "Pending", PendingLedgerPayment.id != p.id,
                    )
                ) or 0
                already_posted = db.scalar(
                    select(func.count()).select_from(AccountLedgerEntry).where(
                        AccountLedgerEntry.source_type == "return", AccountLedgerEntry.source_id == p.source_id,
                    )
                ) or 0
                if order is not None and not still_active and not already_posted:
                    order.accounts_return_processed_at = None
    db.commit()
    return [_pending_payment_out(db, p) for p in rows]


@router.get("/vendors")
def list_vendors(
    state: Optional[str] = None, district: Optional[str] = None, phone: Optional[str] = None,
    code: Optional[str] = None, q: Optional[str] = None,
    db: Session = Depends(get_db), user: User = Depends(get_current_user),
):
    _require(db, user, "vendor", "can_view")
    stmt = select(Vendor).where(Vendor.deleted_at.is_(None))
    if state:
        stmt = stmt.where(Vendor.state == state)
    if district:
        stmt = stmt.where(Vendor.district == district)
    if phone:
        stmt = stmt.where(Vendor.contact_mobile.ilike(f"%{phone.strip()}%"))
    if code:
        stmt = stmt.where(Vendor.vendor_code.ilike(f"%{code.strip()}%"))
    if q:
        stmt = stmt.where(Vendor.name_of_firm.ilike(f"%{q.strip()}%"))
    vendors = db.scalars(stmt.order_by(Vendor.name_of_firm).limit(100)).all()
    out = []
    for v in vendors:
        entries = _entries(db, "vendor", v.id)
        balance = compute_balance(entries)
        overdue = compute_overdue_days(compute_oldest_unpaid_since(entries), v.payment_cycle_days)
        out.append({
            "id": v.id, "name": v.name_of_firm, "code": v.vendor_code, "phone": v.contact_mobile,
            "gst_no": v.gst_no, "balance": float(balance), "overdue_days": overdue,
        })
    return out


@router.get("/engineers")
def list_engineers(
    state: Optional[str] = None, district: Optional[str] = None, phone: Optional[str] = None,
    q: Optional[str] = None,
    db: Session = Depends(get_db), user: User = Depends(get_current_user),
):
    _require(db, user, "engineer", "can_view")
    stmt = select(User).where(User.deleted_at.is_(None))
    stmt = stmt.where(func.lower(func.trim(User.role)).in_(["engineer", "engineer non gst", "engineer_non_gst", "engineer non-gst", "engineer nongst"]))
    if state:
        stmt = stmt.where(User.state == state)
    if district:
        stmt = stmt.where(User.district == district)
    if phone:
        stmt = stmt.where(User.phone.ilike(f"%{phone.strip()}%"))
    if q:
        stmt = stmt.where(or_(User.name.ilike(f"%{q.strip()}%"), User.id == (int(q) if q.isdigit() else -1)))
    users = db.scalars(stmt.order_by(User.name).limit(100)).all()
    out = []
    for u in users:
        entries = _entries(db, "engineer", u.id)
        balance = compute_balance(entries)
        overdue = compute_overdue_days(compute_oldest_unpaid_since(entries), u.payment_cycle_days)
        out.append({
            "id": u.id, "name": u.name, "code": f"ENG-{u.id:04d}", "phone": u.phone,
            "role": u.role, "balance": float(balance), "overdue_days": overdue,
        })
    return out


@router.get("/{party_type}/{party_id}")
def get_ledger(party_type: PartyType, party_id: int, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    _require(db, user, party_type, "can_view")
    party = _load_party(db, party_type, party_id)
    can_edit = can_act_on(db, user, MODULE_FOR[party_type], "can_edit", None)
    return _detail(db, party_type, party_id, party, can_edit)


class OpeningBalanceIn(BaseModel):
    amount: float = Field(ge=0)
    entry_type: Literal["credit", "debit"]
    as_of: Optional[date] = None


@router.post("/{party_type}/{party_id}/opening-balance")
def set_opening_balance(
    party_type: PartyType, party_id: int, body: OpeningBalanceIn,
    db: Session = Depends(get_db), user: User = Depends(get_current_user),
):
    _require(db, user, party_type, "can_edit")
    party = _load_party(db, party_type, party_id)
    existing = db.scalar(
        select(AccountLedgerEntry).where(
            AccountLedgerEntry.party_type == party_type, AccountLedgerEntry.party_id == party_id,
            AccountLedgerEntry.source_type == "opening",
        )
    )
    entry_date = body.as_of or (existing.entry_date if existing else datetime.now(timezone.utc).date())
    if existing:
        existing.amount = body.amount
        existing.entry_type = body.entry_type
        existing.entry_date = entry_date
        existing.description = "Opening balance"
    else:
        db.add(AccountLedgerEntry(
            party_type=party_type, party_id=party_id, entry_type=body.entry_type, amount=body.amount,
            description="Opening balance", source_type="opening", entry_date=entry_date,
            created_by_user_id=user.id,
        ))
    db.commit()
    return _detail(db, party_type, party_id, party, True)


class CycleIn(BaseModel):
    payment_cycle_days: Optional[int] = Field(default=None, ge=1, le=365)


@router.post("/{party_type}/{party_id}/cycle")
def set_cycle(
    party_type: PartyType, party_id: int, body: CycleIn,
    db: Session = Depends(get_db), user: User = Depends(get_current_user),
):
    _require(db, user, party_type, "can_edit")
    party = _load_party(db, party_type, party_id)
    party.payment_cycle_days = body.payment_cycle_days
    db.commit()
    return _detail(db, party_type, party_id, party, True)


class EntryIn(BaseModel):
    entry_type: Literal["credit", "debit"]
    amount: float = Field(gt=0)
    description: str = Field(min_length=2)
    entry_date: Optional[date] = None
    source_type: Literal["manual", "bank_statement", "return"] = "manual"
    source_id: Optional[int] = None


@router.post("/{party_type}/{party_id}/entries")
def add_entry(
    party_type: PartyType, party_id: int, body: EntryIn,
    db: Session = Depends(get_db), user: User = Depends(get_current_user),
):
    _require(db, user, party_type, "can_edit")
    party = _load_party(db, party_type, party_id)
    entry_date = body.entry_date or datetime.now(timezone.utc).date()
    if body.entry_type == "debit" and not is_system_admin(user):
        _create_pending_payment(
            db, party_type=party_type, party_id=party_id, amount=body.amount, description=body.description,
            source_type=body.source_type, source_id=body.source_id, entry_date=entry_date, raised_by_user_id=user.id,
        )
    else:
        db.add(AccountLedgerEntry(
            party_type=party_type, party_id=party_id, entry_type=body.entry_type, amount=body.amount,
            description=body.description, source_type=body.source_type, source_id=body.source_id,
            entry_date=entry_date, created_by_user_id=user.id,
            audit_bypassed=body.entry_type == "debit",
        ))
    db.commit()
    return _detail(db, party_type, party_id, party, True)



@router.get("/dashboard")
def dashboard(db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    if not (can_act_on(db, user, "vendor_ledger", "can_edit", None) or can_act_on(db, user, "engineer_ledger", "can_edit", None)):
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Your role cannot view the ledger dashboard")

    today = datetime.now(timezone.utc).date()
    month_start = today.replace(day=1)

    all_entries = list(db.scalars(select(AccountLedgerEntry)).all())
    by_party: dict[tuple[str, int], list[AccountLedgerEntry]] = {}
    for e in all_entries:
        by_party.setdefault((e.party_type, e.party_id), []).append(e)

    total_due = Decimal("0")
    paid_this_month = Decimal("0")
    overdue_amount = Decimal("0")
    overdue_rows = []
    for e in all_entries:
        if e.entry_type == "debit" and e.entry_date >= month_start:
            paid_this_month += Decimal(str(e.amount))

    vendors = {v.id: v for v in db.scalars(select(Vendor).where(Vendor.deleted_at.is_(None))).all()}
    engineers = {u.id: u for u in db.scalars(select(User).where(User.deleted_at.is_(None))).all()}

    for (party_type, party_id), entries in by_party.items():
        party = vendors.get(party_id) if party_type == "vendor" else engineers.get(party_id)
        if party is None:
            continue
        balance = compute_balance(entries)
        total_due += balance
        oldest = compute_oldest_unpaid_since(entries)
        overdue_days = compute_overdue_days(oldest, party.payment_cycle_days)
        if overdue_days > 0 and balance > 0:
            overdue_amount += balance
            overdue_rows.append({
                "party_type": party_type, "party_id": party_id, "name": _party_name(party, party_type),
                "cycle_days": party.payment_cycle_days, "oldest_unpaid_since": oldest,
                "overdue_days": overdue_days, "balance": float(balance),
            })
    overdue_rows.sort(key=lambda r: -r["overdue_days"])

    month_wise = []
    for i in range(5, -1, -1):
        m_start = (month_start.replace(day=1) - timedelta(days=30 * i)).replace(day=1)
        m_end_month = m_start.month % 12 + 1
        m_end_year = m_start.year + (1 if m_start.month == 12 else 0)
        m_end = m_start.replace(year=m_end_year, month=m_end_month)
        due = sum((Decimal(str(e.amount)) for e in all_entries if e.entry_type == "credit" and m_start <= e.entry_date < m_end), Decimal("0"))
        paid = sum((Decimal(str(e.amount)) for e in all_entries if e.entry_type == "debit" and m_start <= e.entry_date < m_end), Decimal("0"))
        month_wise.append({"month": m_start.strftime("%Y-%m"), "due": float(due), "paid": float(paid)})

    return {
        "total_due": float(total_due),
        "paid_this_month": float(paid_this_month),
        "overdue_amount": float(overdue_amount),
        "overdue_count": len(overdue_rows),
        "overdue": overdue_rows,
        "month_wise": month_wise,
    }
