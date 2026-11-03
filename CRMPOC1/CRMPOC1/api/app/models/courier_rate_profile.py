from sqlalchemy import ForeignKey, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base
from app.models._mixins import TimestampMixin


class CourierRateProfile(Base, TimestampMixin):
    """One courier's whole rate card -- zone definitions, the zone-to-zone rate matrix, overhead
    charges, ODA slabs and the fuel-hike formula -- kept as one JSON blob rather than a dozen
    small tables, since it's edited as a whole profile (fill it in once, change a number when the
    courier revises rates) rather than queried row-by-row."""
    __tablename__ = "courier_rate_profiles"

    courier_id: Mapped[int] = mapped_column(ForeignKey("couriers.id"), primary_key=True)
    profile_json: Mapped[str] = mapped_column(Text, nullable=False)
