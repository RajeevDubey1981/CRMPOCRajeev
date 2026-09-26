"""Import the first 20 orders from the OrderMaster CSV export.

Run from the api/ directory:
    python scripts/import_orders.py

Behaviour:
  - Vendors referenced in the CSV are looked up by name; created if missing.
  - Couriers referenced in the CSV are looked up by name; created if missing.
  - Orders whose order_no already exists are SKIPPED (not duplicated).
  - HTML badge markup in the Status column is stripped to plain text.
"""
import re
import sys
import os
from datetime import date

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy import select

from app.database import SessionLocal
from app.models.order import Order
from app.models.vendor import Vendor
from app.models.courier import Courier

VENDOR_EMAILS = {
    "SAVITAR SERVICES PVT LTD": "vivek.s@pia-consultancy.com",
}

# ---------------------------------------------------------------------------
# Raw CSV data — first 20 rows (IDs 6-25)
# Columns: order_no, order_date, oem_bill_no, status_html, vendor_name,
#          courier_name, lrn_no, vendor_bill_no, vendor_bill_date, expected_delivery
# ---------------------------------------------------------------------------
ORDERS_RAW = [
    ("GEMC-511687730897838", "2024-11-24", "IND69",  "<span class='badge bg-warning'>In Transit</span>",  "PRIMATEL FIBCOM LIMITED",       "Courier2",         "",                  "",                   "",           "2024-11-27"),
    ("GEMC-511687733921049", "2024-11-21", "IND 70", "<span class='badge bg-warning'>In Transit</span>",  "PRIMATEL FIBCOM LIMITED",       "",                 "",                  "",                   "",           ""),
    ("GEMC-511687793715346", "2024-11-23", "IND86",  "<span class='badge bg-warning'>In Transit</span>",  "PRIMATEL FIBCOM LIMITED",       "",                 "",                  "",                   "",           "2024-12-08"),
    ("GEMC-511687746976524", "2024-11-26", "IND82",  "<span class='badge bg-warning'>In Transit</span>",  "PRIMATEL FIBCOM LIMITED",       "",                 "NOTI/24-25/219",    "NOTI/24-25/219",     "2024-12-10", "2024-12-11"),
    ("GEMC-511687767566405", "2024-11-25", "",       "<span class='badge bg-info'>Pending</span>",         "PRIMATEL FIBCOM LIMITED",       "",                 "",                  "",                   "",           "2024-12-10"),
    ("GEMC-511687745023128", "2024-11-25", "IND77",  "<span class='badge bg-warning'>In Transit</span>",  "PRIMATEL FIBCOM LIMITED",       "Delhivery Limited","LRN 272058734",     "NOTI/24-25/207",     "2024-12-05", "2024-12-10"),
    ("GEMC-511687776201378", "2024-11-28", "IND74",  "<span class='badge bg-warning'>In Transit</span>",  "PRIMATEL FIBCOM LIMITED",       "Delhivery Limited","271935885",         "NOTI/24-25/201",     "2024-11-30", "2024-12-13"),
    ("GEMC-511687772763251", "2024-11-27", "IND 79", "<span class='badge bg-warning'>In Transit</span>",  "PRIMATEL FIBCOM LIMITED",       "",                 "",                  "",                   "",           "2024-12-12"),
    ("GEMC-511687774701818", "2024-11-28", "IND75",  "<span class='badge bg-warning'>In Transit</span>",  "PRIMATEL FIBCOM LIMITED",       "Delhivery Limited","272055437",         "NOTI/24-25/205",     "2024-12-04", "2024-12-05"),
    ("abc",                  "2024-11-29", "",       "<span class='badge bg-danger'>Returned</span>",      "Shri Ram Frim",                 "Delhivery Limited","Test LRN",          "Test abc",           "2024-11-29", "2024-11-29"),
    ("511687742681816",      "2024-10-30", "IND125", "<span class='badge bg-success'>Delivered</span>",   "SAVITAR SERVICES PVT LTD",      "Delhivery Limited","271705524",         "SAV/FY24-25/293",    "2024-11-14", "2024-11-27"),
    ("GEMC-511687727134408", "2024-10-28", "",       "<span class='badge bg-success'>Delivered</span>",   "SAVITAR SERVICES PVT LTD",      "Delhivery Limited","271705045",         "SAV/EY24-25/288",    "2024-11-12", "2024-11-12"),
    ("GEMC-511687746670812", "2024-11-29", "IND71",  "<span class='badge bg-warning'>In Transit</span>",  "APPEXIAL PRIVATE LIMITED",      "",                 "",                  "",                   "",           ""),
    ("GEMC-511687720405861", "2024-11-08", "COM247", "<span class='badge bg-success'>Delivered</span>",   "SAVITAR SERVICES PVT LTD",      "Delhivery Limited","",                  "SAV/FY24-25/316",    "2024-11-22", "2024-11-23"),
    ("GEMC-511687761604809", "2024-11-19", "COM247", "<span class='badge bg-success'>Delivered</span>",   "SAVITAR SERVICES PVT LTD",      "Delhivery Limited","",                  "SAV/FY24-25/324",    "2024-11-27", "2024-12-04"),
    ("GEMC-511687793876028", "2024-11-21", "COM247", "<span class='badge bg-success'>Delivered</span>",   "SAVITAR SERVICES PVT LTD",      "Delhivery Limited","",                  "SAV/FY24-25/327",    "2024-11-27", "2024-12-06"),
    ("GEMC-511687714559698", "2024-11-11", "COM248", "<span class='badge bg-success'>Delivered</span>",   "SAVITAR SERVICES PVT LTD",      "Delhivery Limited","",                  "SAV/FY24-25/319",    "2024-11-26", "2024-11-26"),
    ("GEMC-511687763824642", "2024-11-08", "COM248", "<span class='badge bg-success'>Delivered</span>",   "SAVITAR SERVICES PVT LTD",      "Delhivery Limited","273238762",         "SAV/FY24-25/315",    "2024-11-22", "2024-11-23"),
    ("GEMC-511687776701905", "2024-11-20", "COM248", "<span class='badge bg-success'>Delivered</span>",   "SAVITAR SERVICES PVT LTD",      "Delhivery Limited","271965328",         "SAV/FY24-25/325",    "2024-11-27", "2024-12-05"),
    ("GEMC-511687791857609", "2024-11-26", "COM248", "<span class='badge bg-success'>Delivered</span>",   "SAVITAR SERVICES PVT LTD",      "Delhivery Limited","271965922",         "SAV/FY24-25/328",    "2024-11-30", "2024-12-11"),
    ("GEMC-511688001234567", "2024-12-02", "IND130", "<span class='badge bg-warning'>In Transit</span>", "APPEXIAL PRIVATE LIMITED", "Blue Dart", "LRN 272100111", "APP/24-25/310", "2024-12-06", "2024-12-14"),
    ("GEMC-511688002345678", "2024-12-03", "IND131", "<span class='badge bg-success'>Delivered</span>", "PRIMATEL FIBCOM LIMITED", "Delhivery Limited", "LRN 272100112", "NOTI/24-25/250", "2024-12-07", "2024-12-10"),
    ("GEMC-511688003456789", "2024-12-05", "IND132", "<span class='badge bg-info'>Pending</span>", "SAVITAR SERVICES PVT LTD", "", "", "", "", "2024-12-20"),
    ("GEMC-511688004567890", "2024-12-07", "IND133", "<span class='badge bg-danger'>Returned</span>", "Shri Ram Frim", "DTDC", "LRN 272100113", "TEST/24-25/111", "2024-12-09", "2024-12-12"),
    ("GEMC-511688005678901", "2024-12-09", "IND134", "<span class='badge bg-success'>Delivered</span>", "APPEXIAL PRIVATE LIMITED", "Delhivery Limited", "LRN 272100114", "APP/24-25/315", "2024-12-12", "2024-12-16"),
    ("GEMC-511688006789012", "2024-12-11", "IND135", "<span class='badge bg-warning'>In Transit</span>", "PRIMATEL FIBCOM LIMITED", "Blue Dart", "LRN 272100115", "NOTI/24-25/260", "2024-12-14", "2024-12-20"),
    ("GEMC-511688007890123", "2024-12-12", "IND136", "<span class='badge bg-info'>Pending</span>", "SAVITAR SERVICES PVT LTD", "", "", "", "", "2024-12-22"),
    ("GEMC-511688008901234", "2024-12-14", "IND137", "<span class='badge bg-success'>Delivered</span>", "APPEXIAL PRIVATE LIMITED", "Delhivery Limited", "LRN 272100116", "APP/24-25/320", "2024-12-17", "2024-12-21"),
]


def strip_badge(html: str) -> str:
    """Extract plain text from a Bootstrap badge span, e.g. 'In Transit'."""
    text = re.sub(r"<[^>]+>", "", html).strip()
    return text if text else "Pending"


def parse_date(s: str) -> date | None:
    s = s.strip()
    if not s:
        return None
    return date.fromisoformat(s)


def get_or_create_vendor(db, name: str, vendor_cache: dict) -> int | None:
    if not name:
        return None
    vendor_email = VENDOR_EMAILS.get(name.upper())
    if name in vendor_cache:
        return vendor_cache[name]
    vendor = db.scalar(
        select(Vendor).where(Vendor.name_of_firm == name, Vendor.deleted_at.is_(None))
    )
    if vendor is None:
        # Generate a simple vendor_code from the name
        code = "V-" + re.sub(r"[^A-Z0-9]", "", name.upper())[:10]
        # Ensure uniqueness by appending a counter if needed
        base = code
        counter = 1
        while db.scalar(select(Vendor).where(Vendor.vendor_code == code)):
            code = f"{base}{counter}"
            counter += 1
        vendor = Vendor(vendor_code=code, name_of_firm=name, email=vendor_email, is_active=True)
        db.add(vendor)
        db.flush()
        print(f"[vendor+] Created: {name} (code={code})")
    elif vendor_email and vendor.email != vendor_email:
        vendor.email = vendor_email
        db.flush()
        print(f"[vendor~] Updated email: {name} ({vendor_email})")
    vendor_cache[name] = vendor.id
    return vendor.id


def get_or_create_courier(db, name: str, courier_cache: dict) -> int | None:
    if not name:
        return None
    if name in courier_cache:
        return courier_cache[name]
    courier = db.scalar(
        select(Courier).where(Courier.courier_name == name, Courier.deleted_at.is_(None))
    )
    if courier is None:
        courier = Courier(courier_name=name)
        db.add(courier)
        db.flush()
        print(f"[courier+] Created: {name}")
    courier_cache[name] = courier.id
    return courier.id


def main() -> None:
    inserted = skipped = 0
    vendor_cache: dict[str, int] = {}
    courier_cache: dict[str, int] = {}

    with SessionLocal() as db:
        for (order_no, order_date_str, oem_bill_no, status_html, vendor_name,
             courier_name, lrn_no, vendor_bill_no, vendor_bill_date_str,
             expected_delivery_str) in ORDERS_RAW:

            # Skip if already exists
            existing = db.scalar(select(Order).where(Order.order_no == order_no))
            if existing:
                print(f"[skip]   {order_no} — already exists")
                skipped += 1
                continue

            status = strip_badge(status_html)
            vendor_id = get_or_create_vendor(db, vendor_name.strip(), vendor_cache)
            courier_id = get_or_create_courier(db, courier_name.strip(), courier_cache)

            order = Order(
                order_no=order_no.strip(),
                order_date=parse_date(order_date_str) or date.today(),
                oem_bill_no=oem_bill_no.strip() or None,
                vendor_id=vendor_id,
                courier_id=courier_id,
                lrn_no=lrn_no.strip() or None,
                vendor_bill_no=vendor_bill_no.strip() or None,
                vendor_bill_date=parse_date(vendor_bill_date_str),
                status=status,
                expected_delivery_date=parse_date(expected_delivery_str),
            )
            db.add(order)
            print(f"[insert] {order_no} — {status} / {vendor_name}")
            inserted += 1

        db.commit()

    print(f"\n✓ Done: {inserted} inserted, {skipped} skipped.")


if __name__ == "__main__":
    main()
