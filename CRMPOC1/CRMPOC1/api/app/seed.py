"""Seed the database with an admin user and a few sample item masters.

Run after migrations: ``python -m app.seed``
Idempotent — safe to run repeatedly.
"""
from sqlalchemy import inspect, select, text

from app.config import settings
from app.database import SessionLocal
from app.database import engine
from app.data.complaint_models import COMPLAINT_MODEL_CATEGORY, COMPLAINT_MODEL_ITEMS
from app.models.item_master import ItemMaster
from app.models.order import OrderConsigneeAddress
from app.models.role import Permission, Role
from app.models.user import User
from app.security import hash_password, verify_password

SAMPLE_ITEMS = [
    ("8908012210436", "SPLIT AC IDCACS18K5", "AC"),
    ("8908012210443", "WINDOW AC IDCACW15K3", "AC"),
    ("8908012210450", "GEYSER IDCGYS25L", "Geyser"),
    ("8908012210467", "FRIDGE IDCFRD250L", "Fridge"),
    ("8908012210474", "AIR COOLER IDCCLR40L", "Cooler"),
    ("8908012210481", "SPLIT AC IDCACS24K5", "AC"),
    ("8908012210498", "WINDOW AC IDCACW18K3", "AC"),
    ("8908012210504", "GEYSER IDCGYS15L", "Geyser"),
    ("8908012210511", "FRIDGE IDCFRD320L", "Fridge"),
    ("8908012210528", "AIR COOLER IDCCLR60L", "Cooler"),
    ("8908012210535", "SPLIT AC IDCACS13K3E", "AC"),
    ("8908012210542", "WINDOW AC IDCACW24K3E", "AC"),
    ("8908012210559", "GEYSER IDCWH35L", "Geyser"),
    ("8908012210566", "FRIDGE IDCFRD360L", "Fridge"),
    ("8908012210573", "AIR COOLER IDCCLR80L", "Cooler"),
]

SAMPLE_ENGINEERS = [
    ("Ravi Kumar", "ravi@indcool.com", "engineer123", "9810000001"),
    ("Sunita Patel", "sunita@indcool.com", "engineer123", "9810000002"),
    ("Arjun Sharma", "arjun@indcool.com", "engineer123", "9810000003"),
]

VENDOR_EMAIL_LINKS = {
    "SAVITAR SERVICES PVT LTD": "vivek.s@pia-consultancy.com",
}


def ensure_service_payment_columns() -> None:
    inspector = inspect(engine)
    columns = {column["name"] for column in inspector.get_columns("service_payment_requests")}
    if "payment_qr_code_path" not in columns:
        with engine.begin() as conn:
            conn.execute(text("ALTER TABLE service_payment_requests ADD COLUMN payment_qr_code_path VARCHAR(500) NULL"))
        print("[seed] added service_payment_requests.payment_qr_code_path")
    if "approved_amount" not in columns:
        with engine.begin() as conn:
            conn.execute(text("ALTER TABLE service_payment_requests ADD COLUMN approved_amount NUMERIC(12, 2) NULL"))
        print("[seed] added service_payment_requests.approved_amount")


def ensure_service_completion_code_column() -> None:
    inspector = inspect(engine)
    columns = {column["name"] for column in inspector.get_columns("service_requests")}
    if "completion_code" not in columns:
        with engine.begin() as conn:
            conn.execute(text("ALTER TABLE service_requests ADD COLUMN completion_code VARCHAR(10) NULL"))
            conn.execute(text("CREATE INDEX ix_service_requests_completion_code ON service_requests (completion_code)"))
        print("[seed] added service_requests.completion_code")


def ensure_engineer_completion_code_column() -> None:
    inspector = inspect(engine)
    columns = {column["name"] for column in inspector.get_columns("service_completions")}
    if "engineer_completion_code" not in columns:
        with engine.begin() as conn:
            conn.execute(text("ALTER TABLE service_completions ADD COLUMN engineer_completion_code VARCHAR(10) NULL"))
        print("[seed] added service_completions.engineer_completion_code")


def ensure_order_consignee_addresses_table() -> None:
    inspector = inspect(engine)
    if "order_consignee_addresses" in inspector.get_table_names():
        return
    OrderConsigneeAddress.__table__.create(engine)
    print("[seed] created order_consignee_addresses table")


def ensure_order_item_service_columns() -> None:
    inspector = inspect(engine)
    columns = {column["name"] for column in inspector.get_columns("order_items")}
    with engine.begin() as conn:
        if "dry_free_service_count" not in columns:
            conn.execute(text("ALTER TABLE order_items ADD COLUMN dry_free_service_count INT NOT NULL DEFAULT 0"))
            print("[seed] added order_items.dry_free_service_count")
        if "wet_free_service_count" not in columns:
            conn.execute(text("ALTER TABLE order_items ADD COLUMN wet_free_service_count INT NOT NULL DEFAULT 0"))
            print("[seed] added order_items.wet_free_service_count")


def ensure_vendor_type_column() -> None:
    inspector = inspect(engine)
    columns = {column["name"] for column in inspector.get_columns("vendors")}
    if "vendor_type" not in columns:
        add_column_sql = (
            "ALTER TABLE vendors ADD vendor_type VARCHAR(100) NULL"
            if settings.database_backend.strip().lower() == "sqlserver"
            else "ALTER TABLE vendors ADD COLUMN vendor_type VARCHAR(100) NULL"
        )
        with engine.begin() as conn:
            conn.execute(text(add_column_sql))
        print("[seed] added vendors.vendor_type")


def ensure_partner_registration_email_controls() -> None:
    inspector = inspect(engine)
    columns = {column["name"] for column in inspector.get_columns("partner_registrations")}
    if "email_resend_used" in columns:
        return

    column_type = "BIT" if settings.database_backend.strip().lower() == "sqlserver" else "BOOLEAN"
    with engine.begin() as conn:
        conn.execute(
            text(
                f"ALTER TABLE partner_registrations "
                f"ADD COLUMN email_resend_used {column_type} NOT NULL DEFAULT 0"
            )
        )
    print("[seed] added partner_registrations.email_resend_used")

# Default roles and their per-module permissions, derived from spec section 6.
# Flags: (view, create, edit, delete, export)
ALL = (True, True, True, True, True)
RO = (True, False, False, False, True)
NONE = (False, False, False, False, False)
RO_VIEW = (True, False, False, False, False)

DEFAULT_ROLES = [
    {
        "name": "admin",
        "description": "Administrator — full access to all modules",
        "perms": {
            "complaints": ALL, "installations": ALL, "orders": ALL, "vendors": ALL,
            "items": ALL, "couriers": ALL, "calls": ALL, "claims": ALL,
            "users": ALL, "roles": ALL, "dashboard": ALL, "services": ALL,
            "store_receiving": ALL, "store_approval": ALL, "store_stock": ALL, "store_dispatch": ALL,
        },
    },
    {
        "name": "sub_admin",
        "description": "Sub Admin - works like Admin but cannot change roles/permissions or manage Admin accounts",
        "perms": {
            "complaints": ALL, "installations": ALL, "orders": ALL, "vendors": ALL,
            "items": ALL, "couriers": ALL, "calls": ALL, "claims": ALL,
            "dashboard": ALL, "services": ALL, "partner_registrations": ALL,
            "users": (True, True, True, False, False),
            "roles": NONE,
            "payments": (True, False, False, False, False),
            "email_logs": (True, False, False, False, False),
            "store_receiving": ALL, "store_approval": ALL, "store_stock": ALL, "store_dispatch": ALL,
        },
    },
    {
        "name": "store_keeper",
        "description": "Store Keeper - receives goods with a GRN and sees stock; cannot approve",
        "perms": {
            "complaints": NONE, "installations": NONE, "orders": RO_VIEW, "vendors": NONE,
            "items": RO_VIEW, "couriers": NONE, "calls": NONE, "claims": NONE,
            "users": NONE, "roles": NONE, "dashboard": RO_VIEW, "services": NONE,
            "store_receiving": (True, True, True, False, False),
            "store_approval": NONE,
            "store_stock": RO_VIEW,
            "store_dispatch": (True, True, False, False, False),
        },
    },
    {
        "name": "store_manager",
        "description": "Store Manager - approves and posts GRNs, reads stock and exports reports",
        "perms": {
            "complaints": NONE, "installations": NONE, "orders": RO_VIEW, "vendors": NONE,
            "items": RO_VIEW, "couriers": NONE, "calls": NONE, "claims": NONE,
            "users": NONE, "roles": NONE, "dashboard": RO_VIEW, "services": RO_VIEW,
            "store_receiving": (True, True, True, False, True),
            "store_approval": (True, False, True, False, False),
            "store_stock": (True, False, False, False, True),
            "store_dispatch": (True, True, True, False, True),
        },
    },
    {
        "name": "callcenter",
        "description": "Call Center — create/view complaints, log calls",
        "perms": {
            "complaints": (True, True, True, False, True),
            "calls": (True, True, True, False, True),
            "dashboard": RO,
            "items": RO,
            "installations": RO,
            "services": (True, True, False, False, False),
            "orders": RO,
            "vendors": NONE, "couriers": NONE, "claims": NONE,
            "users": NONE, "roles": NONE,
        },
    },
    {
        "name": "engineer",
        "description": "Engineer — view assigned complaints/installations, update status & work reports",
        "perms": {
            "complaints": (True, False, True, False, False),
            "installations": (True, False, True, False, False),
            "services": (True, False, True, False, False),
            "dashboard": RO,
            "items": RO,
            "orders": NONE, "vendors": NONE, "couriers": NONE, "calls": NONE,
            "claims": NONE, "users": NONE, "roles": NONE,
        },
    },
    {
        "name": "vendor",
        "description": "Vendor — read-only access to own orders",
        "perms": {
            "orders": (True, True, False, False, True),
            "services": (True, False, True, False, False),
            "dashboard": RO,
            "complaints": NONE, "installations": NONE, "vendors": NONE, "items": NONE,
            "couriers": NONE, "calls": NONE, "claims": NONE, "users": NONE, "roles": NONE,
        },
    },
    {
        "name": "public",
        "description": "Public User — submit complaint via public form (no login UI)",
        "perms": {
            "complaints": (False, True, False, False, False),
            "installations": NONE, "orders": NONE, "vendors": NONE, "items": NONE,
            "couriers": NONE, "calls": NONE, "claims": NONE, "users": NONE, "services": NONE,
            "roles": NONE, "dashboard": NONE,
        },
    },
    # Sample sub-module-scoped role. The empty parent "complaints" row means
    # this role has no module-wide complaint access; the only access is via the
    # "Sales" query_type sub-module row below.
    {
        "name": "sales",
        "description": "Sales — Sales-type complaints plus order list view",
        "perms": {
            "complaints": NONE,
            "installations": NONE, "orders": (True, False, False, False, False), "vendors": NONE, "items": NONE,
            "couriers": NONE, "calls": NONE, "claims": NONE, "users": NONE, "services": NONE,
            "roles": NONE, "dashboard": RO,
        },
        "sub_perms": {
            ("complaints", "Sales"): (True, True, True, False, True),
        },
    },
    {
        "name": "service",
        "description": "Service desk user — works only on service requests assigned to them",
        "perms": {
            "complaints": ALL, "installations": ALL, "orders": ALL, "vendors": ALL,
            "items": ALL, "couriers": ALL, "calls": ALL, "claims": ALL,
            "services": ALL, "dashboard": ALL,
            "users": NONE, "roles": NONE,
        },
    },
    {
        "name": "service_manager",
        "description": "Service Manager — full service operations access and assign service desk users",
        "perms": {
            "complaints": ALL, "installations": ALL, "orders": ALL, "vendors": ALL,
            "items": ALL, "couriers": ALL, "calls": ALL, "claims": ALL,
            "services": ALL, "dashboard": ALL,
            "users": NONE, "roles": NONE,
        },
    },
    {
        "name": "indcool_service",
        "description": "Indcool Service team - full operations access (no system admin menu)",
        "perms": {
            "complaints": ALL, "installations": ALL, "orders": ALL, "vendors": ALL,
            "items": ALL, "couriers": ALL, "calls": ALL, "claims": ALL,
            "services": ALL, "dashboard": ALL,
            "users": NONE, "roles": NONE,
        },
    },
]


def seed_admin(db) -> None:
    """Ensure admin user exists. Never overwrites an existing admin password (deploy-safe)."""
    existing = db.scalar(select(User).where(User.email == settings.seed_admin_email))
    if existing:
        existing.is_active = True
        if settings.seed_admin_name:
            existing.name = settings.seed_admin_name
        db.commit()
        print(f"[seed] admin already exists (password unchanged): {settings.seed_admin_email}")
        return
    admin = User(
        name=settings.seed_admin_name,
        email=settings.seed_admin_email,
        password_hash=hash_password(settings.seed_admin_password),
        role="admin",
        is_active=True,
    )
    db.add(admin)
    db.commit()
    print(f"[seed] admin created: {settings.seed_admin_email} / {settings.seed_admin_password}")


def seed_items(db) -> None:
    for code, name, category in SAMPLE_ITEMS:
        if db.scalar(select(ItemMaster).where(ItemMaster.item_code == code)):
            continue
        db.add(ItemMaster(item_code=code, item_name=name, category=category))
    db.commit()
    print(f"[seed] item_masters ensured ({len(SAMPLE_ITEMS)} entries)")


def seed_complaint_models(db) -> None:
    from app.services.complaint_model_masters import ensure_complaint_model_masters

    changed = ensure_complaint_model_masters(db)
    print(f"[seed] complaint model masters ensured ({changed} inserted/repaired, {len(COMPLAINT_MODEL_ITEMS)} total)")


def seed_engineers(db) -> None:
    created = 0
    for name, email, password, phone in SAMPLE_ENGINEERS:
        if db.scalar(select(User).where(User.email == email)):
            continue
        db.add(User(
            name=name,
            email=email,
            password_hash=hash_password(password),
            role="engineer",
            phone=phone,
            is_active=True,
        ))
        created += 1
    db.commit()
    print(f"[seed] engineers ensured (created {created} new)")


def _ensure_perm(db, role_id: int, module: str, sub_module: str | None, flags: tuple) -> None:
    v, c, e, d, ex = flags
    existing = db.scalar(
        select(Permission).where(
            Permission.role_id == role_id,
            Permission.module == module,
            Permission.sub_module.is_(sub_module) if sub_module is None else Permission.sub_module == sub_module,
        )
    )
    if existing is None:
        db.add(Permission(
            role_id=role_id, module=module, sub_module=sub_module,
            can_view=v, can_create=c, can_edit=e, can_delete=d, can_export=ex,
        ))


def seed_roles(db) -> None:
    for entry in DEFAULT_ROLES:
        role = db.scalar(select(Role).where(Role.name == entry["name"]))
        if role is None:
            role = Role(name=entry["name"], description=entry["description"])
            db.add(role)
            db.flush()
        elif role.description != entry["description"]:
            role.description = entry["description"]

        for module, flags in entry["perms"].items():
            _ensure_perm(db, role.id, module, None, flags)
        for (module, sub), flags in entry.get("sub_perms", {}).items():
            _ensure_perm(db, role.id, module, sub, flags)
        # Existing rows are left as-is — the matrix UI is the source of truth post-seed.
    db.commit()
    print(f"[seed] roles ensured ({len(DEFAULT_ROLES)} roles)")


def seed_sample_sales_user(db) -> None:
    email = "sales@indcool.com"
    if db.scalar(select(User).where(User.email == email)):
        return
    db.add(User(
        name="Priya Mehta",
        email=email,
        password_hash=hash_password("sales123"),
        role="sales",
        phone="9810010101",
        is_active=True,
    ))
    db.commit()
    print(f"[seed] sample sales user created: {email} / sales123")


def seed_sample_service_user(db) -> None:
    email = "service@indcool.com"
    if db.scalar(select(User).where(User.email == email)):
        return
    db.add(User(
        name="Rohit Verma",
        email=email,
        password_hash=hash_password("service123"),
        role="indcool_service",
        phone="9810020202",
        is_active=True,
    ))
    db.commit()
    print(f"[seed] sample service user created: {email} / service123")


def ensure_vendor_email_links(db) -> None:
    from app.models.vendor import Vendor

    updated = 0
    for firm_name, email in VENDOR_EMAIL_LINKS.items():
        vendor = db.scalar(
            select(Vendor).where(
                Vendor.name_of_firm == firm_name,
                Vendor.deleted_at.is_(None),
            )
        )
        if vendor is None or vendor.email == email:
            continue
        vendor.email = email
        updated += 1
    if updated:
        db.commit()
    print(f"[seed] vendor email links ensured ({updated} updated)")


def seed_sample_service_complaint(db) -> None:
    # Import inside the function to keep the top-level imports lean.
    import secrets
    import time
    from datetime import date, timedelta

    from app.models.complaint import Complaint, ComplaintStatusLog

    admin = db.scalar(select(User).where(User.email == settings.seed_admin_email))
    creator_id = admin.id if admin else None
    base_ts = int(time.time() * 1000)

    samples = [
        {
            "comp_no": f"IDC_SEED_{base_ts + 1}",
            "customer_name": "Demo Service Customer",
            "customer_mobile": "9990000001",
            "customer_email": "demo-service@example.com",
            "customer_address": "Sector 21, Noida, UP",
            "model_details": "SPLIT AC IDCACS18K5",
            "problem_description": "AC compressor making rattling noise; intermittent cooling.",
            "query_type": "Service",
            "status": "Pending",
            "remark": "Seeded sample Service complaint",
        },
        {
            "comp_no": f"IDC_SEED_{base_ts + 2}",
            "customer_name": "Demo Installation Customer",
            "customer_mobile": "9990000002",
            "customer_email": "demo-install@example.com",
            "customer_address": "Sector 18, Gurugram, HR",
            "model_details": "WINDOW AC IDCACW18K3",
            "problem_description": "Customer wants installation coordination for new AC unit.",
            "query_type": "Installation",
            "status": "In Process",
            "remark": "Seeded sample Installation complaint",
        },
        {
            "comp_no": f"IDC_SEED_{base_ts + 3}",
            "customer_name": "Demo Sales Prospect",
            "customer_mobile": "9990000003",
            "customer_email": "demo-sales@example.com",
            "customer_address": "Plot 9, Pune, MH",
            "model_details": "GEYSER IDCGYS15L",
            "problem_description": "Interested in bulk purchase for commercial premises.",
            "query_type": "Sales",
            "status": "Pending",
            "remark": "Seeded sample Sales complaint",
        },
        {
            "comp_no": f"IDC_SEED_{base_ts + 4}",
            "customer_name": "Nitin Bansal",
            "customer_mobile": "9990000004",
            "customer_email": "nitin.bansal@example.com",
            "customer_address": "Sector 62, Noida, UP",
            "model_details": "SPLIT AC IDCACS24K5",
            "problem_description": "Customer reports unusual noise after startup.",
            "query_type": "Service",
            "status": "Pending",
            "remark": "Seeded additional service complaint",
        },
        {
            "comp_no": f"IDC_SEED_{base_ts + 5}",
            "customer_name": "Anjali Rao",
            "customer_mobile": "9990000005",
            "customer_email": "anjali.rao@example.com",
            "customer_address": "Whitefield, Bengaluru, KA",
            "model_details": "FRIDGE IDCFRD360L",
            "problem_description": "Customer wants a service visit for cooling issue.",
            "query_type": "Service",
            "status": "In Process",
            "remark": "Seeded additional service complaint",
        },
    ]

    created = 0
    for sample in samples:
        if db.scalar(select(Complaint).where(Complaint.customer_mobile == sample["customer_mobile"])):
            continue

        complaint = Complaint(
            comp_no=sample["comp_no"],
            comp_date=date.today() - timedelta(days=1),
            customer_name=sample["customer_name"],
            customer_mobile=sample["customer_mobile"],
            customer_email=sample["customer_email"],
            customer_address=sample["customer_address"],
            model_details=sample["model_details"],
            problem_description=sample["problem_description"],
            query_type=sample["query_type"],
            status=sample["status"],
            access_code=f"{secrets.randbelow(1_000_000):06d}",
            send_sms=True,
            source="callcenter",
            created_by=creator_id,
        )
        db.add(complaint)
        db.flush()
        db.add(ComplaintStatusLog(
            complaint_id=complaint.id,
            old_status=None,
            new_status=sample["status"],
            changed_by=creator_id,
            remark=sample["remark"],
        ))
        created += 1

    db.commit()
    print(f"[seed] sample complaints ensured ({created} new)")


def seed_sample_installations(db) -> None:
    from datetime import datetime, timedelta, timezone
    from app.models.installation import InstallationRequest

    installations = [
        ("Amit Patel", "9876543210", "Ghaziabad, UP", "Split AC 2 Ton", 0, "Pending"),
        ("Neha Singh", "9876543211", "Sector 5, Noida", "Window AC 1.5 Ton", 1, "Assigned"),
        ("Rajesh Kumar", "9876543212", "Greater Noida", "Geyser 25L", 2, "In Progress"),
        ("Meera Rao", "9876543213", "Faridabad", "Fridge 250L", 0, "Assigned"),
        ("Sanjay Bhatia", "9876543214", "Jaipur", "Air Cooler 40L", 1, "Pending"),
        ("Pooja Sharma", "9876543215", "Pune", "Split AC 1.2 Ton", 2, "In Progress"),
        ("Vikram Sethi", "9876543216", "Lucknow", "Split AC 1.5 Ton", 0, "Assigned"),
        ("Kiran Malhotra", "9876543217", "Chandigarh", "Window AC 2 Ton", 1, "Pending"),
        ("Deepak Joshi", "9876543218", "Nagpur", "Geyser 25L", 2, "In Progress"),
    ]

    for i, (name, phone, addr, product, eng_idx, status) in enumerate(installations):
        existing = db.scalar(select(InstallationRequest).where(InstallationRequest.contact_number == phone))
        if existing:
            continue

        engineer = None
        if eng_idx is not None and eng_idx < len(SAMPLE_ENGINEERS):
            eng_user = db.scalar(select(User).where(User.email == SAMPLE_ENGINEERS[eng_idx][1]))
            engineer = eng_user.id if eng_user else None

        inst = InstallationRequest(
            customer_name=name,
            contact_number=phone,
            address=addr,
            product_name=product,
            request_date=datetime.now(timezone.utc) - timedelta(days=i*2),
            status=status,
            assigned_engineer=engineer,
        )
        db.add(inst)
    db.commit()
    print(f"[seed] sample installations ensured ({len(installations)} entries)")


def seed_sample_vendor(db) -> None:
    from app.models.vendor import Vendor

    vendor = db.scalar(select(Vendor).where(Vendor.email == "vendor@indcool.com"))
    if vendor:
        return

    vendor = Vendor(
        vendor_code="VEND-001",
        name_of_firm="Vendor Test Co",
        contact_name="Vendor User",
        contact_mobile="9876543200",
        email="vendor@indcool.com",
        gst_no="27AAPPU1234A1Z0",
        address="New Delhi",
        state="Delhi",
        district="Central Delhi",
        pincode="110001",
        is_active=True,
    )
    db.add(vendor)
    db.commit()
    print(f"[seed] vendor created: {vendor.email}")


def seed_sample_vendor1_user_and_orders(db) -> None:
    from datetime import date, timedelta

    from app.models.order import Order, OrderItem
    from app.models.vendor import Vendor

    email = "vendor1@indcool.com"
    password = "vendor123"

    user = db.scalar(select(User).where(User.email == email))
    if user is None:
        user = User(
            name="Vendor One",
            email=email,
            password_hash=hash_password(password),
            role="vendor",
            phone="9876543201",
            is_active=True,
        )
        db.add(user)
        db.flush()
        print(f"[seed] vendor user created: {email} / {password}")
    else:
        if user.role != "vendor":
            user.role = "vendor"
        if not user.is_active:
            user.is_active = True
        if not verify_password(password, user.password_hash):
            user.password_hash = hash_password(password)
            print(f"[seed] vendor1 password reset: {email} / {password}")
        db.flush()

    vendor = db.scalar(select(Vendor).where(Vendor.email == email))
    if vendor is None:
        vendor = Vendor(
            vendor_code="VEND-002",
            name_of_firm="Vendor One Pvt Ltd",
            contact_name="Vendor One",
            contact_mobile="9876543201",
            email=email,
            gst_no="27AAECA1234A1Z5",
            address="Gurugram, Haryana",
            state="Haryana",
            district="Gurugram",
            pincode="122001",
            is_active=True,
        )
        db.add(vendor)
        db.flush()
        print(f"[seed] vendor record created: {vendor.name_of_firm}")
    else:
        if vendor.name_of_firm != "Vendor One Pvt Ltd":
            vendor.name_of_firm = "Vendor One Pvt Ltd"
        if vendor.is_active is not True:
            vendor.is_active = True
        db.flush()

    sample_orders = [
        ("V1-ORD-001", date.today() - timedelta(days=2), "Amit Sharma", "9876543210", "Delhi", "Delivered"),
        ("V1-ORD-002", date.today() - timedelta(days=5), "Neha Verma", "9876543211", "Mumbai", "In Transit"),
        ("V1-ORD-003", date.today() - timedelta(days=8), "Rajat Singh", "9876543212", "Bengaluru", "Pending"),
        ("V1-ORD-004", date.today() - timedelta(days=12), "Pooja Rao", "9876543213", "Chennai", "Delivered"),
    ]

    item = db.scalar(select(ItemMaster).where(ItemMaster.deleted_at.is_(None)).order_by(ItemMaster.id))
    item_id = item.id if item else None

    created = 0
    for order_no, order_date, cust_name, cust_phone, city, status in sample_orders:
        if db.scalar(select(Order).where(Order.order_no == order_no)):
            continue

        admin = db.scalar(select(User).where(User.email == settings.seed_admin_email))
        order = Order(
            order_no=order_no,
            order_date=order_date,
            customer_name=cust_name,
            customer_contact=cust_phone,
            customer_city=city,
            status=status,
            vendor_id=vendor.id,
            created_by=admin.id if admin else None,
        )
        db.add(order)
        db.flush()

        if item_id is None:
            continue

        item_qty = 2 if status == "Delivered" else 1
        db.add(OrderItem(
            order_id=order.id,
            item_id=item_id,
            serial_no=f"V1SN{order.id:03d}A",
            serial_no_2=f"V1SN2-{order.id:03d}",
            pcb_warranty_years=1,
            component_warranty_years=2,
            machine_warranty_years=3,
            free_service_count=2,
            service_consume_count=0,
            installation_status="Completed" if status == "Delivered" else "Pending",
            item_qty=item_qty,
        ))
        created += 1

    db.commit()
    print(f"[seed] vendor1 orders ensured ({created} new)")


def seed_sample_orders_with_serials(db) -> None:
    from datetime import date
    from app.models.order import Order, OrderItem
    from app.models.vendor import Vendor

    sample_orders = [
        ("VEND-ORD-201", "2024-07-15", "Cust 1", "9876543210", "Delhi", "Delivered", None),
        ("VEND-ORD-202", "2024-07-20", "Cust 2", "9876543211", "Mumbai", "Delivered", None),
        ("VEND-ORD-203", "2024-07-10", "Cust S", "9990000005", "TestCity", "Pending", None),
        ("VEND-ORD-204", "2024-06-15", "Cust 3", "9876543212", "Bangalore", "In Transit", None),
        ("VEND-ORD-205", "2024-07-25", "Cust 4", "9876543213", "Pune", "Delivered", None),
        ("VEND-ORD-206", "2024-08-01", "Cust 5", "9876543216", "Hyderabad", "Pending", None),
        ("VEND-ORD-207", "2024-08-05", "Cust 6", "9876543217", "Chennai", "In Transit", None),
        ("VEND-ORD-208", "2024-08-10", "Cust 7", "9876543218", "Kolkata", "Delivered", None),
        ("VEND-ORD-209", "2024-08-12", "Cust 8", "9876543219", "Ahmedabad", "Pending", None),
        ("VEND-ORD-210", "2024-08-16", "Cust 9", "9876543220", "Surat", "Delivered", None),
        ("VEND-ORD-211", "2024-08-20", "Cust 10", "9876543221", "Vadodara", "In Transit", None),
        ("VEND-ORD-212", "2024-08-22", "Cust 11", "9876543222", "Coimbatore", "Pending", None),
        ("VEND-ORD-213", "2024-08-25", "Cust 12", "9876543223", "Indore", "Delivered", None),
    ]

    # Get or create vendor for these orders
    vendor = db.scalar(select(Vendor).where(Vendor.email == "vendor@indcool.com"))
    vendor_id = vendor.id if vendor else None
    item = db.scalar(select(ItemMaster).where(ItemMaster.deleted_at.is_(None)).order_by(ItemMaster.id))
    item_id = item.id if item else None

    for order_no, order_date_str, cust_name, cust_phone, city, status, _ in sample_orders:
        existing = db.scalar(select(Order).where(Order.order_no == order_no))
        if existing:
            continue

        admin = db.scalar(select(User).where(User.email == settings.seed_admin_email))
        order = Order(
            order_no=order_no,
            order_date=date.fromisoformat(order_date_str),
            customer_name=cust_name,
            customer_contact=cust_phone,
            customer_city=city,
            status=status,
            vendor_id=vendor_id,
            created_by=admin.id if admin else None,
        )
        db.add(order)
        db.flush()

        # Add sample serials for this order (2-3 per order)
        num_items = 3 if status == "Delivered" else 2
        if item_id is None:
            continue
        for i in range(num_items):
            serial_no = f"SN{order.id:03d}{i+1:02d}"
            serial_no_2 = f"SN2-{order.id}-{i+1:03d}"
            db.add(OrderItem(
                order_id=order.id,
                item_id=item_id,
                serial_no=serial_no,
                serial_no_2=serial_no_2,
                pcb_warranty_years=1,
                component_warranty_years=2,
                machine_warranty_years=3,
                free_service_count=2,
                service_consume_count=0,
                installation_status="Not Requested" if status == "Delivered" else "Pending",
            ))
    db.commit()
    print(f"[seed] sample orders with serials ensured ({len(sample_orders)} orders)")


def seed_sample_partner_registrations(db) -> None:
    from datetime import datetime, timezone

    from app.models.partner_registration import PartnerRegistration
    from app.services.partner_registration import generate_access_token

    samples = [
        ("Partner", "Gem Partner Solutions Pvt Ltd", "9876500101", "partner1@gem.example", "Ravi Kumar", "Documents Verification"),
        ("Distributor", "North India Distributors", "9876500102", "dist1@gem.example", "Anita Sharma", "Admin Review"),
        ("Service Partner", "CoolCare Service Network", "9876500103", "service1@gem.example", "Mohit Singh", "Onboarding Approved"),
        ("Retailer", "City Retail Appliances", "9876500104", "retail1@gem.example", "Priya Nair", "Registration Submitted"),
        ("Partner", "Allied Gem Traders", "9876500105", "partner2@gem.example", "Suresh Patel", "Partner Active"),
    ]
    created = 0
    now = datetime.now(timezone.utc)
    for index, (ptype, name, mobile, email, contact, status) in enumerate(samples, start=1):
        reg_no = f"GEM-PART-{index:05d}"
        exists = db.scalar(
            select(PartnerRegistration).where(PartnerRegistration.registration_no == reg_no)
        )
        if exists:
            continue
        db.add(
            PartnerRegistration(
                registration_no=reg_no,
                access_token=generate_access_token(),
                partner_type=ptype,
                name=name,
                mobile=mobile,
                email=email,
                contact_person_name=contact,
                form_status="Submitted",
                current_form_step=9,
                completion_percent=100,
                onboarding_status=status,
                firm_address="Sample business address",
                city="Mumbai",
                state="Maharashtra",
                pincode="400001",
                gst_no=f"27AABCU9603R{index}ZM",
                gem_seller_id=f"GEM-SELLER-{index:04d}",
                remarks="Sample GeM partner registration",
                invited_at=now,
                form_started_at=now,
                form_submitted_at=now,
                submitted_at=now,
                status_updated_at=now,
                declaration_accepted=True,
            )
        )
        created += 1
    if created:
        db.commit()
    print(f"[seed] partner registrations ensured ({created} new)")


def main() -> None:
    import argparse

    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--minimal",
        action="store_true",
        help="Only seed roles/permissions and the admin user; skip sample/demo data.",
    )
    parser.add_argument(
        "--master-data",
        action="store_true",
        help="Seed roles and non-demo master data such as Product Details dropdown values.",
    )
    parser.add_argument(
        "--no-admin",
        action="store_true",
        help="Do not create or update the bootstrap admin user (use on production deploy).",
    )
    args = parser.parse_args()

    ensure_service_payment_columns()
    ensure_service_completion_code_column()
    ensure_engineer_completion_code_column()
    ensure_order_consignee_addresses_table()
    ensure_order_item_service_columns()
    ensure_vendor_type_column()
    ensure_partner_registration_email_controls()
    with SessionLocal() as db:
        seed_roles(db)
        if not args.no_admin:
            seed_admin(db)
        if args.minimal:
            return
        if args.master_data:
            seed_complaint_models(db)
            return
        seed_items(db)
        seed_complaint_models(db)
        seed_engineers(db)
        seed_sample_sales_user(db)
        seed_sample_service_user(db)
        ensure_vendor_email_links(db)
        seed_sample_service_complaint(db)
        seed_sample_installations(db)
        seed_sample_vendor(db)
        seed_sample_vendor1_user_and_orders(db)
        seed_sample_orders_with_serials(db)
        seed_sample_partner_registrations(db)


if __name__ == "__main__":
    main()
