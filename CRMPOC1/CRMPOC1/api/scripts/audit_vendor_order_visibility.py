"""Audit and repair vendor-user order visibility links.

Vendor users can see orders only when users.email matches vendors.email.
Run from the api/ directory:

    python scripts/audit_vendor_order_visibility.py
    python scripts/audit_vendor_order_visibility.py --apply
    python scripts/audit_vendor_order_visibility.py --apply --create-users
"""
import argparse
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy import func, select

from app.database import SessionLocal
from app.models.order import Order
from app.models.user import User
from app.models.vendor import Vendor
from app.security import hash_password


KNOWN_VENDOR_EMAILS = {
    "SAVITAR SERVICES PVT LTD": "vivek.s@pia-consultancy.com",
}

DEFAULT_VENDOR_PASSWORD = "vendor123"


def normalized_email(value: str | None) -> str:
    return (value or "").strip().lower()


def order_count_by_vendor(db) -> dict[int, int]:
    rows = db.execute(
        select(Order.vendor_id, func.count(Order.id))
        .where(Order.deleted_at.is_(None), Order.vendor_id.is_not(None))
        .group_by(Order.vendor_id)
    ).all()
    return {int(vendor_id): int(count or 0) for vendor_id, count in rows if vendor_id is not None}


def load_users_by_email(db) -> dict[str, User]:
    users = db.scalars(
        select(User).where(
            User.deleted_at.is_(None),
        )
    ).all()
    return {
        normalized_email(user.email): user
        for user in users
        if normalized_email(user.email)
    }


def print_row(status: str, vendor: Vendor, order_count: int, user: User | None) -> None:
    user_bits = "no vendor user"
    if user is not None:
        active = "active" if user.is_active else "inactive"
        user_bits = f"user_id={user.id} {user.email} {active}"
    email = vendor.email or "-"
    print(
        f"{status:12} vendor_id={vendor.id:<5} orders={order_count:<5} "
        f"email={email:<35} firm={vendor.name_of_firm} ({user_bits})"
    )


def audit_and_repair(apply: bool, create_users: bool) -> int:
    with SessionLocal() as db:
        counts = order_count_by_vendor(db)
        users_by_email = load_users_by_email(db)
        vendors = db.scalars(
            select(Vendor)
            .where(Vendor.deleted_at.is_(None))
            .order_by(Vendor.name_of_firm)
        ).all()

        issues = 0
        changes = 0

        for vendor in vendors:
            order_count = counts.get(vendor.id, 0)
            expected_email = KNOWN_VENDOR_EMAILS.get((vendor.name_of_firm or "").strip().upper())
            current_email = normalized_email(vendor.email)

            if expected_email and current_email != expected_email:
                issues += 1
                print_row("FIX-EMAIL", vendor, order_count, users_by_email.get(expected_email))
                if apply:
                    vendor.email = expected_email
                    current_email = expected_email
                    changes += 1

            user = users_by_email.get(current_email) if current_email else None
            if order_count > 0 and not current_email:
                issues += 1
                print_row("NO-EMAIL", vendor, order_count, None)
            elif order_count > 0 and user is not None and (user.role or "").lower() != "vendor":
                issues += 1
                print_row("BAD-ROLE", vendor, order_count, user)
                if apply:
                    user.role = "vendor"
                    if not user.is_active:
                        user.is_active = True
                    changes += 1
            elif order_count > 0 and user is None:
                issues += 1
                print_row("NO-USER", vendor, order_count, None)
                if apply and create_users:
                    user = User(
                        name=vendor.contact_name or vendor.name_of_firm or current_email,
                        email=current_email,
                        password_hash=hash_password(DEFAULT_VENDOR_PASSWORD),
                        role="vendor",
                        phone=vendor.contact_mobile,
                        is_active=True,
                    )
                    db.add(user)
                    db.flush()
                    users_by_email[current_email] = user
                    changes += 1
                    print(f"  created vendor user: {current_email} / {DEFAULT_VENDOR_PASSWORD}")
            elif user is not None and not user.is_active:
                issues += 1
                print_row("INACTIVE", vendor, order_count, user)
                if apply:
                    user.is_active = True
                    changes += 1
            else:
                print_row("OK", vendor, order_count, user)

        if apply and changes:
            db.commit()
        elif apply:
            print("No changes needed.")

        print(f"\nSummary: {issues} issue(s), {changes} change(s){' applied' if apply else ' pending'}")
        return 1 if issues and not apply else 0


def main() -> None:
    parser = argparse.ArgumentParser(description="Audit vendor email links used for order visibility.")
    parser.add_argument("--apply", action="store_true", help="Apply known repairs.")
    parser.add_argument(
        "--create-users",
        action="store_true",
        help="When used with --apply, create missing vendor users for vendors that already have an email.",
    )
    args = parser.parse_args()
    raise SystemExit(audit_and_repair(args.apply, args.create_users))


if __name__ == "__main__":
    main()
