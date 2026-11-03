from pydantic import BaseModel, Field


class ZoneRate(BaseModel):
    from_zone: str
    to_zone: str
    rate_per_kg: float


class OdaSlab(BaseModel):
    weight_from: float
    weight_to: float
    rate_per_kg: float
    min_amount: float


class CourierRateProfileData(BaseModel):
    """Matches a transporter's own rate-card document (see e.g. a Delhivery Annexure III): zone
    definitions, the zone-to-zone matrix, overheads, ODA slabs and the diesel-linked fuel-hike
    formula. Lane-based exceptions (special per-state rates to the North-East/Ladakh) aren't
    captured here yet -- those fall back to the zone matrix until added."""
    zones: list[str] = Field(default_factory=list)  # e.g. ["N1","N2","E","NE","W1","W2","S1","S2","Central"]
    zone_states: dict[str, list[str]] = Field(default_factory=dict)  # zone_code -> state names
    zone_rates: list[ZoneRate] = Field(default_factory=list)
    docket_charge: float = 0
    fsc_percent: float = 0
    volumetric_divisor: float = 5000
    handling_rate_per_kg: float = 0
    handling_min_weight_kg: float = 0
    demurrage_rate_per_kg: float = 0
    demurrage_min_amount: float = 0
    free_storage_days: int = 0
    min_chargeable_weight_kg: float = 0
    min_chargeable_amount: float = 0
    base_diesel_rate: float = 0
    fuel_hike_percent_per_rupee: float = 0
    oda_slabs: list[OdaSlab] = Field(default_factory=list)
    source_zone: str | None = None  # which zone your own warehouse ships from, for freight calc


class CourierRateProfileOut(BaseModel):
    courier_id: int
    profile: CourierRateProfileData


class FreightCalcIn(BaseModel):
    destination_state: str
    weight_kg: float
    volumetric_cu_ft: float | None = None
    is_oda: bool = False


class FreightCalcLine(BaseModel):
    label: str
    amount: float


class FreightCalcOut(BaseModel):
    source_zone: str | None
    destination_zone: str | None
    chargeable_weight_kg: float
    lines: list[FreightCalcLine]
    total: float
