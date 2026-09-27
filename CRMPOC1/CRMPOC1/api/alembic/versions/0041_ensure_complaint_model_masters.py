"""Repair Product Details (complaint model) master rows after deploy.

Revision ID: 0041_ensure_complaint_model_masters
Revises: 0040_order_consignee_addresses
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "0041_ensure_complaint_model_masters"
down_revision: Union[str, None] = "0040_order_consignee_addresses"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

COMPLAINT_MODEL_CATEGORY = "Complaint Model"
COMPLAINT_MODEL_ITEMS = [
    ("IDC-CM-WAC", "Window AC"),
    ("IDC-CM-SAC", "Split AC"),
    ("IDC-CM-FRG", "Fridge"),
    ("IDC-CM-GYS", "Geyser"),
    ("IDC-CM-WCL", "Water Cooler"),
    ("IDC-CM-ACL", "Air Cooler"),
]


def upgrade() -> None:
    conn = op.get_bind()
    for code, name in COMPLAINT_MODEL_ITEMS:
        conn.execute(
            sa.text(
                """
                UPDATE item_masters
                SET category = :category,
                    item_name = :name,
                    is_active = 1,
                    deleted_at = NULL,
                    updated_at = CURRENT_TIMESTAMP(6)
                WHERE item_code = :code
                """
            ),
            {"code": code, "name": name, "category": COMPLAINT_MODEL_CATEGORY},
        )
        exists = conn.execute(
            sa.text("SELECT 1 FROM item_masters WHERE item_code = :code LIMIT 1"),
            {"code": code},
        ).first()
        if exists:
            continue
        conn.execute(
            sa.text(
                """
                INSERT INTO item_masters (
                    item_code, item_name, category, serial_count, is_active, created_at, updated_at
                ) VALUES (
                    :code, :name, :category, 1, 1, CURRENT_TIMESTAMP(6), CURRENT_TIMESTAMP(6)
                )
                """
            ),
            {"code": code, "name": name, "category": COMPLAINT_MODEL_CATEGORY},
        )


def downgrade() -> None:
    pass
