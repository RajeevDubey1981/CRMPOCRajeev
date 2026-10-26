"""The vendor/engineer Dr-Cr ledger. Two party types share one table (AccountLedgerEntry) and one
balance/overdue calculation; everything else here is just which party type a call is about.

Permissions: "vendor_ledger" and "engineer_ledger" are ordinary permission modules (Admin -> Roles),
can_view for read-only access, can_edit for setting an opening balance/payment cycle or adding an entry.
"""

from __future__ import annotations

from datetime import date, datetime, timedelta, timezone
from decimal import Decimal
from typing import Literal, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, Field
from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session

from app.database import get_db
from app.deps import get_current_user
from app.models.account_ledger import AccountLedgerEntry
from app.models.user import User
from app.models.vendor import Vendor
from app.services.account_ledger import compute_balance, compute_oldest_unpaid_since, compute_overdue_days
from app.services.permissions import can_act_on
from app.services.role_access import role_key

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
    }


def _detail(db: Session, party_type: PartyType, party_id: int, party, can_edit: bool) -> dict:
    entries = _entries(db, party_type, party_id)
    balance = compute_balance(entries)
    oldest_unpaid = compute_oldest_unpaid_since(entries)
    cycle_days = party.payment_cycle_days
    overdue_days = compute_overdue_days(oldest_unpaid, cycle_days)
    opening = next((e for e in entries if e.source_type == "opening"), None)
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
        "entries": [_entry_out(e) for e in entries],
    }


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
    db.add(AccountLedgerEntry(
        party_type=party_type, party_id=party_id, entry_type=body.entry_type, amount=body.amount,
        description=body.description, source_type=body.source_type, source_id=body.source_id,
        entry_date=body.entry_date or datetime.now(timezone.utc).date(),
        created_by_user_id=user.id,
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
