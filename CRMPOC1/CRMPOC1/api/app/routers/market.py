import secrets
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session

from app.database import get_db
from app.deps import get_current_user
from app.services.role_access import is_system_admin
from app.models.market import (
    MarketCategory,
    MarketItem,
    MarketOrder,
    MarketOrderItem,
    MarketUser,
)
from app.models.user import User
from app.schemas.market import (
    MarketCategoryCreate,
    MarketCategoryOut,
    MarketCategoryUpdate,
    MarketDashboard,
    MarketItemCreate,
    MarketItemListResponse,
    MarketItemOut,
    MarketItemUpdate,
    MarketOrderCreate,
    MarketOrderItemOut,
    MarketOrderListItem,
    MarketOrderListResponse,
    MarketOrderOut,
    MarketOrderUpdate,
    MarketUserCreate,
    MarketUserListResponse,
    MarketUserLookup,
    MarketUserOut,
    MarketUserUpdate,
)

router = APIRouter(prefix="/api/market", tags=["market"])


def _require_admin(user: User = Depends(get_current_user)) -> User:
    # Market Admin has never had a real permission card -- the Sidebar hides it from everyone but
    # system admins client-side (systemAdminOnly), but nothing on the server ever enforced that, so any
    # logged-in account of any role could hit these routes directly (security review, 2026-10-27).
    if not is_system_admin(user):
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Insufficient permissions")
    return user


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _generate_order_no() -> str:
    return f"ORD{datetime.now().strftime('%Y%m%d')}{secrets.randbelow(10000):04d}"


def _category_name(db: Session, category_id: int | None) -> str | None:
    if category_id is None:
        return None
    cat = db.get(MarketCategory, category_id)
    return cat.name if cat else None


def _user_name(db: Session, user_id: int | None) -> str | None:
    if user_id is None:
        return None
    mu = db.get(MarketUser, user_id)
    return mu.name if mu else None


def _item_name(db: Session, item_id: int | None) -> str | None:
    if item_id is None:
        return None
    mi = db.get(MarketItem, item_id)
    return mi.name if mi else None


def _hydrate_order(db: Session, order: MarketOrder) -> MarketOrderOut:
    order_items = db.scalars(
        select(MarketOrderItem).where(MarketOrderItem.order_id == order.id)
    ).all()
    items_out = [
        MarketOrderItemOut(
            id=oi.id,
            item_id=oi.item_id,
            item_name=_item_name(db, oi.item_id),
            qty=oi.qty,
            unit_price=float(oi.unit_price) if oi.unit_price is not None else None,
            subtotal=float(oi.subtotal) if oi.subtotal is not None else None,
        )
        for oi in order_items
    ]
    return MarketOrderOut(
        id=order.id,
        order_no=order.order_no,
        retailer_id=order.retailer_id,
        retailer_name=_user_name(db, order.retailer_id),
        distributor_id=order.distributor_id,
        distributor_name=_user_name(db, order.distributor_id),
        total_amount=float(order.total_amount) if order.total_amount is not None else None,
        status=order.status,
        notes=order.notes,
        created_at=order.created_at,
        items=items_out,
    )


# ---------------------------------------------------------------------------
# Dashboard
# ---------------------------------------------------------------------------

@router.get("/dashboard", response_model=MarketDashboard)
def get_dashboard(
    db: Session = Depends(get_db),
    _user: User = Depends(_require_admin),
):
    total_users = db.scalar(select(func.count(MarketUser.id))) or 0
    active_users = db.scalar(
        select(func.count(MarketUser.id)).where(MarketUser.status == "Active")
    ) or 0
    pending_users = db.scalar(
        select(func.count(MarketUser.id)).where(MarketUser.status == "Pending")
    ) or 0

    total_items = db.scalar(select(func.count(MarketItem.id))) or 0
    active_items = db.scalar(
        select(func.count(MarketItem.id)).where(MarketItem.status == "Active")
    ) or 0
    low_stock_items = db.scalar(
        select(func.count(MarketItem.id)).where(MarketItem.stock_count <= 5)
    ) or 0

    total_orders = db.scalar(select(func.count(MarketOrder.id))) or 0
    pending_orders = db.scalar(
        select(func.count(MarketOrder.id)).where(MarketOrder.status == "Pending")
    ) or 0
    delivered_orders = db.scalar(
        select(func.count(MarketOrder.id)).where(MarketOrder.status == "Delivered")
    ) or 0
    total_sales = db.scalar(
        select(func.sum(MarketOrder.total_amount)).where(
            MarketOrder.status != "Cancelled"
        )
    ) or 0.0

    total_categories = db.scalar(select(func.count(MarketCategory.id))) or 0

    return MarketDashboard(
        total_users=total_users,
        active_users=active_users,
        pending_users=pending_users,
        total_items=total_items,
        active_items=active_items,
        low_stock_items=low_stock_items,
        total_orders=total_orders,
        pending_orders=pending_orders,
        delivered_orders=delivered_orders,
        total_sales=float(total_sales),
        total_categories=total_categories,
    )


# ---------------------------------------------------------------------------
# Market Users — lookup MUST be defined before /{id}
# ---------------------------------------------------------------------------

@router.get("/users/lookup", response_model=list[MarketUserLookup])
def lookup_users(
    db: Session = Depends(get_db),
    _user: User = Depends(_require_admin),
):
    rows = db.scalars(
        select(MarketUser).order_by(MarketUser.name)
    ).all()
    return [MarketUserLookup(id=r.id, name=r.name, role=r.role) for r in rows]


@router.get("/users", response_model=MarketUserListResponse)
def list_users(
    page: int = Query(1, ge=1),
    per_page: int = Query(20, ge=1, le=200),
    status_filter: str | None = Query(None, alias="status"),
    role: str | None = Query(None),
    search: str | None = Query(None),
    db: Session = Depends(get_db),
    _user: User = Depends(_require_admin),
):
    stmt = select(MarketUser)
    if status_filter:
        stmt = stmt.where(MarketUser.status == status_filter)
    if role:
        stmt = stmt.where(MarketUser.role == role)
    if search:
        like = f"%{search.strip()}%"
        stmt = stmt.where(
            or_(
                MarketUser.name.ilike(like),
                MarketUser.email.ilike(like),
            )
        )
    stmt = stmt.order_by(MarketUser.id.desc())
    total = db.scalar(select(func.count()).select_from(stmt.subquery())) or 0
    rows = db.scalars(stmt.offset((page - 1) * per_page).limit(per_page)).all()
    items = [
        MarketUserOut(
            id=r.id,
            name=r.name,
            email=r.email,
            phone=r.phone,
            address=r.address,
            city=r.city,
            state=r.state,
            role=r.role,
            status=r.status,
            fee_status=r.fee_status,
            onboarding_fee=float(r.onboarding_fee) if r.onboarding_fee is not None else None,
            joined_at=r.joined_at,
            created_at=r.created_at,
        )
        for r in rows
    ]
    return MarketUserListResponse(items=items, total=total, page=page, per_page=per_page)


@router.post("/users", response_model=MarketUserOut, status_code=status.HTTP_201_CREATED)
def create_user(
    body: MarketUserCreate,
    db: Session = Depends(get_db),
    _user: User = Depends(_require_admin),
):
    existing = db.scalar(select(MarketUser).where(MarketUser.email == body.email))
    if existing:
        raise HTTPException(status.HTTP_409_CONFLICT, "Email already registered")
    mu = MarketUser(**body.model_dump())
    db.add(mu)
    db.commit()
    db.refresh(mu)
    return MarketUserOut(
        id=mu.id,
        name=mu.name,
        email=mu.email,
        phone=mu.phone,
        address=mu.address,
        city=mu.city,
        state=mu.state,
        role=mu.role,
        status=mu.status,
        fee_status=mu.fee_status,
        onboarding_fee=float(mu.onboarding_fee) if mu.onboarding_fee is not None else None,
        joined_at=mu.joined_at,
        created_at=mu.created_at,
    )


@router.get("/users/{user_id}", response_model=MarketUserOut)
def get_user(
    user_id: int,
    db: Session = Depends(get_db),
    _user: User = Depends(_require_admin),
):
    mu = db.get(MarketUser, user_id)
    if mu is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Market user not found")
    return MarketUserOut(
        id=mu.id,
        name=mu.name,
        email=mu.email,
        phone=mu.phone,
        address=mu.address,
        city=mu.city,
        state=mu.state,
        role=mu.role,
        status=mu.status,
        fee_status=mu.fee_status,
        onboarding_fee=float(mu.onboarding_fee) if mu.onboarding_fee is not None else None,
        joined_at=mu.joined_at,
        created_at=mu.created_at,
    )


@router.put("/users/{user_id}", response_model=MarketUserOut)
def update_user(
    user_id: int,
    body: MarketUserUpdate,
    db: Session = Depends(get_db),
    _user: User = Depends(_require_admin),
):
    mu = db.get(MarketUser, user_id)
    if mu is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Market user not found")
    for field, value in body.model_dump(exclude_unset=True).items():
        setattr(mu, field, value)
    db.commit()
    db.refresh(mu)
    return MarketUserOut(
        id=mu.id,
        name=mu.name,
        email=mu.email,
        phone=mu.phone,
        address=mu.address,
        city=mu.city,
        state=mu.state,
        role=mu.role,
        status=mu.status,
        fee_status=mu.fee_status,
        onboarding_fee=float(mu.onboarding_fee) if mu.onboarding_fee is not None else None,
        joined_at=mu.joined_at,
        created_at=mu.created_at,
    )


@router.delete("/users/{user_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_user(
    user_id: int,
    db: Session = Depends(get_db),
    _user: User = Depends(_require_admin),
):
    mu = db.get(MarketUser, user_id)
    if mu is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Market user not found")
    db.delete(mu)
    db.commit()


# ---------------------------------------------------------------------------
# Market Categories
# ---------------------------------------------------------------------------

@router.get("/categories", response_model=list[MarketCategoryOut])
def list_categories(
    db: Session = Depends(get_db),
    _user: User = Depends(_require_admin),
):
    categories = db.scalars(select(MarketCategory).order_by(MarketCategory.id)).all()

    # Build lookup maps
    parent_names: dict[int, str] = {c.id: c.name for c in categories}
    item_counts: dict[int, int] = {}
    child_counts: dict[int, int] = {}

    for cat in categories:
        count = db.scalar(
            select(func.count(MarketItem.id)).where(MarketItem.category_id == cat.id)
        ) or 0
        item_counts[cat.id] = count

        cc = db.scalar(
            select(func.count(MarketCategory.id)).where(
                MarketCategory.parent_id == cat.id
            )
        ) or 0
        child_counts[cat.id] = cc

    return [
        MarketCategoryOut(
            id=c.id,
            name=c.name,
            parent_id=c.parent_id,
            parent_name=parent_names.get(c.parent_id) if c.parent_id else None,
            item_count=item_counts.get(c.id, 0),
            child_count=child_counts.get(c.id, 0),
            created_at=c.created_at,
        )
        for c in categories
    ]


@router.post("/categories", response_model=MarketCategoryOut, status_code=status.HTTP_201_CREATED)
def create_category(
    body: MarketCategoryCreate,
    db: Session = Depends(get_db),
    _user: User = Depends(_require_admin),
):
    cat = MarketCategory(name=body.name, parent_id=body.parent_id)
    db.add(cat)
    db.commit()
    db.refresh(cat)
    parent_name = None
    if cat.parent_id:
        p = db.get(MarketCategory, cat.parent_id)
        parent_name = p.name if p else None
    return MarketCategoryOut(
        id=cat.id,
        name=cat.name,
        parent_id=cat.parent_id,
        parent_name=parent_name,
        item_count=0,
        child_count=0,
        created_at=cat.created_at,
    )


@router.put("/categories/{category_id}", response_model=MarketCategoryOut)
def update_category(
    category_id: int,
    body: MarketCategoryUpdate,
    db: Session = Depends(get_db),
    _user: User = Depends(_require_admin),
):
    cat = db.get(MarketCategory, category_id)
    if cat is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Category not found")
    for field, value in body.model_dump(exclude_unset=True).items():
        setattr(cat, field, value)
    db.commit()
    db.refresh(cat)
    parent_name = None
    if cat.parent_id:
        p = db.get(MarketCategory, cat.parent_id)
        parent_name = p.name if p else None
    item_count = db.scalar(
        select(func.count(MarketItem.id)).where(MarketItem.category_id == cat.id)
    ) or 0
    child_count = db.scalar(
        select(func.count(MarketCategory.id)).where(MarketCategory.parent_id == cat.id)
    ) or 0
    return MarketCategoryOut(
        id=cat.id,
        name=cat.name,
        parent_id=cat.parent_id,
        parent_name=parent_name,
        item_count=item_count,
        child_count=child_count,
        created_at=cat.created_at,
    )


@router.delete("/categories/{category_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_category(
    category_id: int,
    db: Session = Depends(get_db),
    _user: User = Depends(_require_admin),
):
    cat = db.get(MarketCategory, category_id)
    if cat is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Category not found")
    db.delete(cat)
    db.commit()


# ---------------------------------------------------------------------------
# Market Items
# ---------------------------------------------------------------------------

@router.get("/items", response_model=MarketItemListResponse)
def list_items(
    page: int = Query(1, ge=1),
    per_page: int = Query(20, ge=1, le=200),
    status_filter: str | None = Query(None, alias="status"),
    category_id: int | None = Query(None),
    search: str | None = Query(None),
    db: Session = Depends(get_db),
    _user: User = Depends(_require_admin),
):
    stmt = select(MarketItem)
    if status_filter:
        stmt = stmt.where(MarketItem.status == status_filter)
    if category_id:
        stmt = stmt.where(MarketItem.category_id == category_id)
    if search:
        like = f"%{search.strip()}%"
        stmt = stmt.where(
            or_(
                MarketItem.sku.ilike(like),
                MarketItem.name.ilike(like),
            )
        )
    stmt = stmt.order_by(MarketItem.id.desc())
    total = db.scalar(select(func.count()).select_from(stmt.subquery())) or 0
    rows = db.scalars(stmt.offset((page - 1) * per_page).limit(per_page)).all()
    items = [
        MarketItemOut(
            id=r.id,
            sku=r.sku,
            name=r.name,
            company=r.company,
            category_id=r.category_id,
            category_name=_category_name(db, r.category_id),
            base_price=float(r.base_price) if r.base_price is not None else None,
            mrp=float(r.mrp) if r.mrp is not None else None,
            status=r.status,
            stock_count=r.stock_count,
            description=r.description,
            created_at=r.created_at,
        )
        for r in rows
    ]
    return MarketItemListResponse(items=items, total=total, page=page, per_page=per_page)


@router.post("/items", response_model=MarketItemOut, status_code=status.HTTP_201_CREATED)
def create_item(
    body: MarketItemCreate,
    db: Session = Depends(get_db),
    _user: User = Depends(_require_admin),
):
    existing = db.scalar(select(MarketItem).where(MarketItem.sku == body.sku))
    if existing:
        raise HTTPException(status.HTTP_409_CONFLICT, "SKU already exists")
    mi = MarketItem(**body.model_dump())
    db.add(mi)
    db.commit()
    db.refresh(mi)
    return MarketItemOut(
        id=mi.id,
        sku=mi.sku,
        name=mi.name,
        company=mi.company,
        category_id=mi.category_id,
        category_name=_category_name(db, mi.category_id),
        base_price=float(mi.base_price) if mi.base_price is not None else None,
        mrp=float(mi.mrp) if mi.mrp is not None else None,
        status=mi.status,
        stock_count=mi.stock_count,
        description=mi.description,
        created_at=mi.created_at,
    )


@router.get("/items/{item_id}", response_model=MarketItemOut)
def get_item(
    item_id: int,
    db: Session = Depends(get_db),
    _user: User = Depends(_require_admin),
):
    mi = db.get(MarketItem, item_id)
    if mi is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Item not found")
    return MarketItemOut(
        id=mi.id,
        sku=mi.sku,
        name=mi.name,
        company=mi.company,
        category_id=mi.category_id,
        category_name=_category_name(db, mi.category_id),
        base_price=float(mi.base_price) if mi.base_price is not None else None,
        mrp=float(mi.mrp) if mi.mrp is not None else None,
        status=mi.status,
        stock_count=mi.stock_count,
        description=mi.description,
        created_at=mi.created_at,
    )


@router.put("/items/{item_id}", response_model=MarketItemOut)
def update_item(
    item_id: int,
    body: MarketItemUpdate,
    db: Session = Depends(get_db),
    _user: User = Depends(_require_admin),
):
    mi = db.get(MarketItem, item_id)
    if mi is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Item not found")
    for field, value in body.model_dump(exclude_unset=True).items():
        setattr(mi, field, value)
    db.commit()
    db.refresh(mi)
    return MarketItemOut(
        id=mi.id,
        sku=mi.sku,
        name=mi.name,
        company=mi.company,
        category_id=mi.category_id,
        category_name=_category_name(db, mi.category_id),
        base_price=float(mi.base_price) if mi.base_price is not None else None,
        mrp=float(mi.mrp) if mi.mrp is not None else None,
        status=mi.status,
        stock_count=mi.stock_count,
        description=mi.description,
        created_at=mi.created_at,
    )


@router.delete("/items/{item_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_item(
    item_id: int,
    db: Session = Depends(get_db),
    _user: User = Depends(_require_admin),
):
    mi = db.get(MarketItem, item_id)
    if mi is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Item not found")
    db.delete(mi)
    db.commit()


# ---------------------------------------------------------------------------
# Market Orders
# ---------------------------------------------------------------------------

@router.get("/orders", response_model=MarketOrderListResponse)
def list_orders(
    page: int = Query(1, ge=1),
    per_page: int = Query(20, ge=1, le=200),
    status_filter: str | None = Query(None, alias="status"),
    search: str | None = Query(None),
    db: Session = Depends(get_db),
    _user: User = Depends(_require_admin),
):
    stmt = select(MarketOrder)
    if status_filter:
        stmt = stmt.where(MarketOrder.status == status_filter)
    if search:
        like = f"%{search.strip()}%"
        stmt = stmt.where(MarketOrder.order_no.ilike(like))
    stmt = stmt.order_by(MarketOrder.id.desc())
    total = db.scalar(select(func.count()).select_from(stmt.subquery())) or 0
    rows = db.scalars(stmt.offset((page - 1) * per_page).limit(per_page)).all()
    items = [
        MarketOrderListItem(
            id=r.id,
            order_no=r.order_no,
            retailer_name=_user_name(db, r.retailer_id),
            distributor_name=_user_name(db, r.distributor_id),
            total_amount=float(r.total_amount) if r.total_amount is not None else None,
            status=r.status,
            created_at=r.created_at,
        )
        for r in rows
    ]
    return MarketOrderListResponse(items=items, total=total, page=page, per_page=per_page)


@router.post("/orders", response_model=MarketOrderOut, status_code=status.HTTP_201_CREATED)
def create_order(
    body: MarketOrderCreate,
    db: Session = Depends(get_db),
    _user: User = Depends(_require_admin),
):
    # Compute total from items
    total = 0.0
    for it in body.items:
        qty = it.qty or 1
        up = it.unit_price or 0.0
        total += qty * up

    order = MarketOrder(
        order_no=_generate_order_no(),
        retailer_id=body.retailer_id,
        distributor_id=body.distributor_id,
        status=body.status,
        notes=body.notes,
        total_amount=total if total > 0 else None,
    )
    db.add(order)
    db.flush()

    for it in body.items:
        qty = it.qty or 1
        up = it.unit_price
        sub = (qty * float(up)) if up is not None else None
        oi = MarketOrderItem(
            order_id=order.id,
            item_id=it.item_id,
            qty=qty,
            unit_price=up,
            subtotal=sub,
        )
        db.add(oi)

    db.commit()
    db.refresh(order)
    return _hydrate_order(db, order)


@router.get("/orders/{order_id}", response_model=MarketOrderOut)
def get_order(
    order_id: int,
    db: Session = Depends(get_db),
    _user: User = Depends(_require_admin),
):
    order = db.get(MarketOrder, order_id)
    if order is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Order not found")
    return _hydrate_order(db, order)


@router.put("/orders/{order_id}", response_model=MarketOrderOut)
def update_order(
    order_id: int,
    body: MarketOrderUpdate,
    db: Session = Depends(get_db),
    _user: User = Depends(_require_admin),
):
    order = db.get(MarketOrder, order_id)
    if order is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Order not found")
    for field, value in body.model_dump(exclude_unset=True).items():
        setattr(order, field, value)
    db.commit()
    db.refresh(order)
    return _hydrate_order(db, order)


@router.delete("/orders/{order_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_order(
    order_id: int,
    db: Session = Depends(get_db),
    _user: User = Depends(_require_admin),
):
    order = db.get(MarketOrder, order_id)
    if order is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Order not found")
    db.delete(order)
    db.commit()
