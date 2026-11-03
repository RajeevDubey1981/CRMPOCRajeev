"""Per-courier rate card: zone definitions, zone-to-zone matrix, overheads, ODA slabs and the
fuel-hike formula -- plus a freight calculator that uses a saved profile the same way a real OEM
bill would be checked against it."""
from __future__ import annotations

import json

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.database import get_db
from app.deps import get_current_user
from app.models.courier import Courier
from app.models.courier_rate_profile import CourierRateProfile
from app.models.user import User
from app.schemas.courier_rate_profile import (
    CourierRateProfileData,
    CourierRateProfileOut,
    FreightCalcIn,
    FreightCalcLine,
    FreightCalcOut,
)
from app.services.permissions import can_act_on
from app.services.role_access import is_operations_admin

router = APIRouter(prefix="/api/couriers", tags=["couriers"])


def _require_admin(user: User):
    if not is_operations_admin(user):
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Only Admin or Indcool users can access Courier Master.")


def _load_courier(db: Session, courier_id: int) -> Courier:
    c = db.get(Courier, courier_id)
    if c is None or c.deleted_at is not None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Courier not found")
    return c


@router.get("/{courier_id}/rate-profile", response_model=CourierRateProfileOut)
def get_rate_profile(courier_id: int, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    _require_admin(user)
    if not can_act_on(db, user, "couriers", "can_view", None):
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Your role cannot view couriers")
    _load_courier(db, courier_id)
    row = db.get(CourierRateProfile, courier_id)
    data = CourierRateProfileData(**json.loads(row.profile_json)) if row else CourierRateProfileData()
    return CourierRateProfileOut(courier_id=courier_id, profile=data)


@router.put("/{courier_id}/rate-profile", response_model=CourierRateProfileOut)
def save_rate_profile(
    courier_id: int, body: CourierRateProfileData, db: Session = Depends(get_db), user: User = Depends(get_current_user)
):
    _require_admin(user)
    if not can_act_on(db, user, "couriers", "can_edit", None):
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Your role cannot edit couriers")
    _load_courier(db, courier_id)
    row = db.get(CourierRateProfile, courier_id)
    payload = body.model_dump_json()
    if row is None:
        row = CourierRateProfile(courier_id=courier_id, profile_json=payload)
        db.add(row)
    else:
        row.profile_json = payload
    db.commit()
    return CourierRateProfileOut(courier_id=courier_id, profile=body)


def _find_zone_for_state(profile: CourierRateProfileData, state: str) -> str | None:
    needle = (state or "").strip().lower()
    for zone, states in profile.zone_states.items():
        if any(s.strip().lower() == needle for s in states):
            return zone
    return None


def _zone_rate(profile: CourierRateProfileData, from_zone: str, to_zone: str) -> float | None:
    for zr in profile.zone_rates:
        if zr.from_zone == from_zone and zr.to_zone == to_zone:
            return zr.rate_per_kg
    return None


def _volumetric_kg(divisor: float, length_cm, width_cm, height_cm) -> float:
    if length_cm and width_cm and height_cm and divisor:
        return (length_cm * width_cm * height_cm) / divisor
    return 0.0


def _price_shipment(profile: CourierRateProfileData, source_zone, destination_zone, chargeable_weight: float) -> tuple[list[FreightCalcLine], float]:
    lines: list[FreightCalcLine] = []
    rate = None
    if source_zone and destination_zone:
        rate = _zone_rate(profile, source_zone, destination_zone)
    base_amount = (rate or 0) * chargeable_weight
    lines.append(FreightCalcLine(
        label=f"Base rate ({source_zone or '?'} → {destination_zone or '?'}, {rate or 0}/kg × {chargeable_weight}kg)",
        amount=round(base_amount, 2),
    ))

    if profile.docket_charge:
        lines.append(FreightCalcLine(label="Docket charge", amount=profile.docket_charge))

    if profile.fsc_percent:
        fsc = round(base_amount * profile.fsc_percent / 100, 2)
        lines.append(FreightCalcLine(label=f"Fuel surcharge ({profile.fsc_percent}%)", amount=fsc))

    return lines, subtotal


def _add_oda(profile: CourierRateProfileData, lines: list[FreightCalcLine], chargeable_weight: float, is_oda: bool) -> float:
    if not (is_oda and profile.oda_slabs):
        return sum(l.amount for l in lines)
    slab = next(
        (s for s in profile.oda_slabs if s.weight_from <= chargeable_weight < s.weight_to),
        profile.oda_slabs[-1] if profile.oda_slabs else None,
    )
    if slab:
        oda_amount = max(slab.rate_per_kg * chargeable_weight, slab.min_amount)
        lines.append(FreightCalcLine(label="ODA charge", amount=round(oda_amount, 2)))
    return sum(l.amount for l in lines)


def _apply_floor(profile: CourierRateProfileData, lines: list[FreightCalcLine], subtotal: float) -> float:
    if profile.min_chargeable_amount and subtotal < profile.min_chargeable_amount:
        lines.append(FreightCalcLine(
            label=f"Minimum chargeable floor (₹{profile.min_chargeable_amount})",
            amount=round(profile.min_chargeable_amount - subtotal, 2),
        ))
        return profile.min_chargeable_amount
    return subtotal


def calculate_freight(profile: CourierRateProfileData, body: FreightCalcIn) -> FreightCalcOut:
    source_zone = profile.source_zone
    destination_zone = _find_zone_for_state(profile, body.destination_state)
    divisor = profile.volumetric_divisor

    is_two_box = bool(body.box2_weight_kg or (body.box2_length_cm and body.box2_width_cm and body.box2_height_cm))

    if body.weight_only:
        chargeable_weight = max(body.weight_kg + (body.box2_weight_kg or 0), profile.min_chargeable_weight_kg or 0)
        lines, subtotal = _price_shipment(profile, source_zone, destination_zone, chargeable_weight)
        lines.insert(0, FreightCalcLine(label="No dimensions given — charged on actual weight only, no volumetric check", amount=0))
    elif is_two_box:
        vol1 = _volumetric_kg(divisor, body.length_cm, body.width_cm, body.height_cm)
        vol2 = _volumetric_kg(divisor, body.box2_length_cm, body.box2_width_cm, body.box2_height_cm)
        box1_weight = max(body.weight_kg, vol1)
        box2_weight = max(body.box2_weight_kg or 0, vol2)
        chargeable_weight = max(box1_weight + box2_weight, profile.min_chargeable_weight_kg or 0)
        lines, subtotal = _price_shipment(profile, source_zone, destination_zone, chargeable_weight)
        lines.insert(0, FreightCalcLine(
            label=f"2 boxes — box 1 {round(box1_weight, 1)}kg (actual {body.weight_kg}kg vs. vol. {round(vol1, 1)}kg) + box 2 {round(box2_weight, 1)}kg (actual {body.box2_weight_kg or 0}kg vs. vol. {round(vol2, 1)}kg)",
            amount=0,
        ))
    else:
        volumetric_weight = _volumetric_kg(divisor, body.length_cm, body.width_cm, body.height_cm)
        chargeable_weight = max(body.weight_kg, volumetric_weight, profile.min_chargeable_weight_kg or 0)
        lines, subtotal = _price_shipment(profile, source_zone, destination_zone, chargeable_weight)
        if volumetric_weight > 0:
            lines.insert(0, FreightCalcLine(
                label=f"Actual {body.weight_kg}kg vs. volumetric {round(volumetric_weight, 1)}kg — higher one charged",
                amount=0,
            ))

    subtotal = _add_oda(profile, lines, chargeable_weight, body.is_oda)
    subtotal = _apply_floor(profile, lines, subtotal)

    result = FreightCalcOut(
        source_zone=source_zone,
        destination_zone=destination_zone,
        chargeable_weight_kg=chargeable_weight,
        lines=lines,
        total=round(subtotal, 2),
    )

    # If this is a 2-box request that also gave the single-box dimensions, price that alternative
    # too and recommend whichever packing comes out cheaper (ties favour 2 boxes — safer handling).
    if is_two_box and body.single_length_cm and body.single_width_cm and body.single_height_cm:
        single_vol = _volumetric_kg(divisor, body.single_length_cm, body.single_width_cm, body.single_height_cm)
        single_weight = max(body.weight_kg + (body.box2_weight_kg or 0), single_vol, profile.min_chargeable_weight_kg or 0)
        single_lines, single_subtotal = _price_shipment(profile, source_zone, destination_zone, single_weight)
        single_subtotal = _add_oda(profile, single_lines, single_weight, body.is_oda)
        single_subtotal = _apply_floor(profile, single_lines, single_subtotal)
        result.single_box_total = round(single_subtotal, 2)
        result.recommended = "one_box" if single_subtotal < result.total else "two_boxes"

    return result


@router.post("/{courier_id}/calculate-freight", response_model=FreightCalcOut)
def calculate_freight_endpoint(
    courier_id: int, body: FreightCalcIn, db: Session = Depends(get_db), user: User = Depends(get_current_user)
):
    _require_admin(user)
    _load_courier(db, courier_id)
    row = db.get(CourierRateProfile, courier_id)
    if row is None:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "No rate profile saved for this courier yet")
    profile = CourierRateProfileData(**json.loads(row.profile_json))
    return calculate_freight(profile, body)
