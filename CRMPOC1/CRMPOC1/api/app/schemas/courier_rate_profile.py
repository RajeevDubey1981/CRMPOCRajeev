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
    volumetric_divisor: float = 5000  # kg = (L x W x H in cm) / this divisor
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
    destination_pincode: str | None = None  # reference only; flips on is_oda manually for now
    weight_kg: float
    weight_only: bool = False  # True: skip the volumetric check, charge on weight_kg alone
    length_cm: float | None = None
    width_cm: float | None = None
    height_cm: float | None = None
    # Second box, for a shipment packed as 2 pieces (e.g. split AC indoor + outdoor). When given,
    # the engine also prices packing everything as 1 box (single_* fields) and returns both so the
    # cheaper option can be picked.
    box2_weight_kg: float | None = None
    box2_length_cm: float | None = None
    box2_width_cm: float | None = None
    box2_height_cm: float | None = None
    single_length_cm: float | None = None
    single_width_cm: float | None = None
    single_height_cm: float | None = None
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
    # Filled in only when a 2-box request also supplied single_* dimensions: the same shipment
    # priced as 1 combined box, so the cheaper packing can be chosen.
    single_box_total: float | None = None
    recommended: str | None = None  # "two_boxes" | "one_box", when single_box_total is set
