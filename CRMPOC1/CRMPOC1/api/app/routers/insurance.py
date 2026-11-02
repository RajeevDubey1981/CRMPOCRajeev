from app.models.insurance import Insurance
from app.routers._simple_master_factory import make_master_router
from app.schemas.insurance import (
    InsuranceCreate,
    InsuranceListItem,
    InsuranceListResponse,
    InsuranceOut,
    InsuranceUpdate,
)

router = make_master_router(
    model=Insurance,
    create_schema=InsuranceCreate,
    update_schema=InsuranceUpdate,
    out_schema=InsuranceOut,
    list_item_schema=InsuranceListItem,
    list_response_schema=InsuranceListResponse,
    prefix="/api/insurance",
    tag="insurance",
    permission_module="insurance",
    display_name="Insurance",
)
