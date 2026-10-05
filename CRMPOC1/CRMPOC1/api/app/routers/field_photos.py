"""Machine photos taken in the field against a serial, each with the phone's location.

Only the engineer the serial is assigned to can add a photo. Anyone who can see the service request or the
installation can look at the photos and open the spot on a map.
"""

from __future__ import annotations

from datetime import datetime, timezone

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.database import get_db
from app.deps import get_current_user
from app.models.field_photo import FieldPhoto
from app.models.installation import InstallationEngineerSerial
from app.models.service import ServiceRequestUnit
from app.models.user import User
from app.routers.installations import _load_visible as load_visible_installation
from app.routers.services import _load_visible_service
from app.schemas.field_photo import FieldPhotoOut
from app.services.file_service import save_upload, to_public_upload_path
from app.services.role_access import role_key

router = APIRouter(prefix="/api/field-photos", tags=["field-photos"])

MAX_PHOTOS_PER_SERIAL = 6
MAX_PHOTO_BYTES = 5 * 1024 * 1024
IMAGE_EXT = {".jpg", ".jpeg", ".png"}
IMAGE_MIME = {"image/jpeg", "image/jpg", "image/png"}


def _out(db: Session, row: FieldPhoto) -> FieldPhotoOut:
    who = db.get(User, row.uploaded_by_user_id)
    lat, lng = float(row.latitude), float(row.longitude)
    return FieldPhotoOut(
        id=row.id,
        source=row.source,
        serial_no=row.serial_no,
        file_path=to_public_upload_path(row.file_path),
        latitude=lat,
        longitude=lng,
        accuracy_m=float(row.accuracy_m) if row.accuracy_m is not None else None,
        captured_at=row.captured_at,
        created_at=row.created_at,
        uploaded_by_name=who.name if who else None,
        map_url=f"https://www.google.com/maps?q={lat:.7f},{lng:.7f}",
    )


def _check_position(latitude: float, longitude: float, accuracy: float | None) -> None:
    if not (-90 <= latitude <= 90) or not (-180 <= longitude <= 180):
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "The location is not valid")
    if latitude == 0 and longitude == 0:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "The phone could not find its location. Switch location on and try again")
    if accuracy is not None and accuracy < 0:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "The location is not valid")


def _parse_captured_at(value: str | None) -> datetime | None:
    if not value:
        return None
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return None
    return parsed if parsed.tzinfo else parsed.replace(tzinfo=timezone.utc)


def _unit_for_view(db: Session, unit_id: int, user: User) -> ServiceRequestUnit:
    unit = db.get(ServiceRequestUnit, unit_id)
    if unit is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Serial not found")
    _load_visible_service(db, unit.service_request_id, user)  # 404 when the user may not see the request
    return unit


def _serial_for_view(db: Session, serial_id: int, user: User) -> InstallationEngineerSerial:
    row = db.get(InstallationEngineerSerial, serial_id)
    if row is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Serial not found")
    load_visible_installation(db, user, row.installation_request_id)
    return row


async def _store(
    db: Session,
    *,
    source: str,
    unit_id: int | None,
    serial_row_id: int | None,
    serial_no: str | None,
    existing: int,
    photo: UploadFile,
    latitude: float,
    longitude: float,
    accuracy: float | None,
    captured_at: str | None,
    user: User,
) -> FieldPhoto:
    if existing >= MAX_PHOTOS_PER_SERIAL:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, f"A serial can have at most {MAX_PHOTOS_PER_SERIAL} photos")
    _check_position(latitude, longitude, accuracy)
    path = await save_upload(photo, module="field_photos", allowed_ext=IMAGE_EXT, allowed_mime=IMAGE_MIME, max_bytes=MAX_PHOTO_BYTES)
    row = FieldPhoto(
        source=source,
        service_request_unit_id=unit_id,
        installation_engineer_serial_id=serial_row_id,
        serial_no=serial_no,
        file_path=path,
        latitude=round(latitude, 7),
        longitude=round(longitude, 7),
        accuracy_m=round(accuracy, 1) if accuracy is not None else None,
        captured_at=_parse_captured_at(captured_at),
        uploaded_by_user_id=user.id,
    )
    db.add(row)
    db.commit()
    db.refresh(row)
    return row


# ---------------------------------------------------------------- service request units

@router.get("/service-units/{unit_id}", response_model=list[FieldPhotoOut])
def list_for_unit(unit_id: int, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    unit = _unit_for_view(db, unit_id, user)
    rows = db.scalars(select(FieldPhoto).where(FieldPhoto.service_request_unit_id == unit.id).order_by(FieldPhoto.id)).all()
    return [_out(db, r) for r in rows]


@router.post("/service-units/{unit_id}", response_model=FieldPhotoOut, status_code=status.HTTP_201_CREATED)
async def add_for_unit(
    unit_id: int,
    photo: UploadFile = File(...),
    latitude: float = Form(...),
    longitude: float = Form(...),
    accuracy: float | None = Form(None),
    captured_at: str | None = Form(None),
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    unit = _unit_for_view(db, unit_id, user)
    if role_key(user.role) != "engineer" or unit.assigned_engineer_id != user.id:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Only the engineer this serial is assigned to can add a photo")
    existing = len(db.scalars(select(FieldPhoto.id).where(FieldPhoto.service_request_unit_id == unit.id)).all())
    row = await _store(
        db, source="service_unit", unit_id=unit.id, serial_row_id=None, serial_no=unit.serial_no, existing=existing,
        photo=photo, latitude=latitude, longitude=longitude, accuracy=accuracy, captured_at=captured_at, user=user,
    )
    return _out(db, row)


# ---------------------------------------------------------------- installation serials

@router.get("/installation-serials/{serial_id}", response_model=list[FieldPhotoOut])
def list_for_serial(serial_id: int, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    serial = _serial_for_view(db, serial_id, user)
    rows = db.scalars(select(FieldPhoto).where(FieldPhoto.installation_engineer_serial_id == serial.id).order_by(FieldPhoto.id)).all()
    return [_out(db, r) for r in rows]


@router.post("/installation-serials/{serial_id}", response_model=FieldPhotoOut, status_code=status.HTTP_201_CREATED)
async def add_for_serial(
    serial_id: int,
    photo: UploadFile = File(...),
    latitude: float = Form(...),
    longitude: float = Form(...),
    accuracy: float | None = Form(None),
    captured_at: str | None = Form(None),
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    serial = _serial_for_view(db, serial_id, user)
    if role_key(user.role) != "engineer":
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Only the assigned engineer can add a photo")
    existing = len(db.scalars(select(FieldPhoto.id).where(FieldPhoto.installation_engineer_serial_id == serial.id)).all())
    row = await _store(
        db, source="installation_serial", unit_id=None, serial_row_id=serial.id, serial_no=serial.serial_no, existing=existing,
        photo=photo, latitude=latitude, longitude=longitude, accuracy=accuracy, captured_at=captured_at, user=user,
    )
    return _out(db, row)
