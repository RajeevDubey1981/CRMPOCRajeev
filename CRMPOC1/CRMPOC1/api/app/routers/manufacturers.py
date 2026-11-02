from app.models.manufacturer import Manufacturer
from app.routers._simple_master_factory import make_master_router
from app.schemas.manufacturer import (
    ManufacturerCreate,
    ManufacturerListItem,
    ManufacturerListResponse,
    ManufacturerOut,
    ManufacturerUpdate,
)

router = make_master_router(
    model=Manufacturer,
    create_schema=ManufacturerCreate,
    update_schema=ManufacturerUpdate,
    out_schema=ManufacturerOut,
    list_item_schema=ManufacturerListItem,
    list_response_schema=ManufacturerListResponse,
    prefix="/api/manufacturers",
    tag="manufacturers",
    permission_module="manufacturers",
    display_name="Manufacturer",
)
