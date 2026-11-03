from sqlalchemy import Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base
from app.models._mixins import TimestampMixin, SoftDeleteMixin


class Courier(Base, TimestampMixin, SoftDeleteMixin):
    __tablename__ = "couriers"

    id: Mapped[int] = mapped_column(primary_key=True)
    courier_name: Mapped[str] = mapped_column(String(255), nullable=False)
    contact_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    contact_mobile: Mapped[str | None] = mapped_column(String(20), nullable=True)
    email: Mapped[str | None] = mapped_column(String(255), nullable=True)
    address: Mapped[str | None] = mapped_column(Text, nullable=True)
    # Same role as Vendor/User's payment_cycle_days: drives the overdue-days calc on the courier's
    # own ledger tab (account_ledger.py). Null = no cycle set yet, overdue isn't computed.
    payment_cycle_days: Mapped[int | None] = mapped_column(Integer, nullable=True)
