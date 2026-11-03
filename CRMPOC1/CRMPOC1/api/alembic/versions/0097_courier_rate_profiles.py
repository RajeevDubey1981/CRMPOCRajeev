"""Add courier_rate_profiles (one JSON rate-card blob per courier -- zones, the zone-to-zone
matrix, overheads, ODA slabs, fuel-hike formula) and seed Delhivery's from the signed agreement.

Revision ID: 0097_courier_rate_profiles
Revises: 0096_manufacturer_insurance_masters
Create Date: 2026-11-03
"""

import json

from alembic import op
import sqlalchemy as sa


revision = "0097_courier_rate_profiles"
down_revision = "0096_manufacturer_insurance_masters"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "courier_rate_profiles",
        sa.Column("courier_id", sa.Integer(), sa.ForeignKey("couriers.id"), primary_key=True),
        sa.Column("profile_json", sa.Text(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )

    conn = op.get_bind()
    existing = conn.execute(
        sa.text("SELECT id FROM couriers WHERE lower(courier_name) = 'delhivery' AND deleted_at IS NULL LIMIT 1")
    ).fetchone()
    if existing is None:
        result = conn.execute(
            sa.text(
                "INSERT INTO couriers (courier_name, contact_name, email, created_at, updated_at) "
                "VALUES ('Delhivery', 'Legal Department', 'legal@delhivery.com', NOW(), NOW())"
            )
        )
        courier_id = result.lastrowid
    else:
        courier_id = existing[0]

    zone_states = {
        "N1": ["Delhi", "Uttar Pradesh", "Haryana", "Rajasthan"],
        "N2": ["Chandigarh", "Punjab", "Himachal Pradesh", "Uttarakhand", "Jammu & Kashmir", "Ladakh"],
        "E": ["West Bengal", "Odisha", "Bihar", "Jharkhand"],
        "NE": ["Assam", "Meghalaya", "Tripura", "Arunachal Pradesh", "Mizoram", "Manipur", "Nagaland", "Sikkim"],
        "W1": ["Gujarat", "Daman & Diu", "Dadra & Nagar Haveli"],
        "W2": ["Maharashtra", "Goa"],
        "S1": ["Andhra Pradesh", "Telangana", "Karnataka", "Tamil Nadu", "Puducherry"],
        "S2": ["Kerala"],
        "Central": ["Madhya Pradesh", "Chhattisgarh"],
    }
    zones = list(zone_states.keys())
    matrix = {
        "N1": {"N1": 5.92, "N2": 6.41, "E": 12.31, "NE": 22.55, "W1": 7.65, "W2": 10.75, "S1": 14.42, "S2": 18.40, "Central": 10.06},
        "N2": {"N1": 7.67, "N2": 7.27, "E": 15.62, "NE": 23.76, "W1": 11.46, "W2": 12.95, "S1": 18.49, "S2": 23.05, "Central": 12.50},
        "E": {"N1": 9.11, "N2": 10.67, "E": 8.03, "NE": 13.94, "W1": 9.94, "W2": 9.12, "S1": 11.57, "S2": 15.14, "Central": 8.43},
        "NE": {"N1": 7.16, "N2": 10.32, "E": 7.34, "NE": 11.31, "W1": 8.29, "W2": 10.14, "S1": 12.22, "S2": 11.21, "Central": 8.35},
        "W1": {"N1": 11.08, "N2": 11.05, "E": 18.21, "NE": 28.95, "W1": 6.83, "W2": 9.75, "S1": 15.39, "S2": 18.64, "Central": 10.64},
        "W2": {"N1": 11.19, "N2": 13.66, "E": 17.05, "NE": 26.37, "W1": 8.83, "W2": 7.96, "S1": 11.84, "S2": 15.12, "Central": 10.35},
        "S1": {"N1": 11.72, "N2": 13.37, "E": 14.26, "NE": 22.73, "W1": 9.53, "W2": 7.76, "S1": 8.73, "S2": 9.58, "Central": 11.28},
        "S2": {"N1": 12.73, "N2": 15.38, "E": 17.23, "NE": 25.95, "W1": 10.06, "W2": 8.51, "S1": 7.51, "S2": 6.87, "Central": 12.06},
        "Central": {"N1": 7.78, "N2": 9.57, "E": 12.37, "NE": 21.51, "W1": 6.33, "W2": 6.94, "S1": 13.20, "S2": 16.63, "Central": 8.87},
    }
    zone_rates = [
        {"from_zone": f, "to_zone": t, "rate_per_kg": matrix[f][t]}
        for f in zones for t in zones
    ]

    profile = {
        "zones": zones,
        "zone_states": zone_states,
        "zone_rates": zone_rates,
        "docket_charge": 200,
        "fsc_percent": 20.0,
        "volumetric_divisor": 4500,
        "handling_rate_per_kg": 3,
        "handling_min_weight_kg": 400,
        "demurrage_rate_per_kg": 1,
        "demurrage_min_amount": 100,
        "free_storage_days": 4,
        "min_chargeable_weight_kg": 25,
        "min_chargeable_amount": 350,
        "base_diesel_rate": 98.13,
        "fuel_hike_percent_per_rupee": 0.40,
        "oda_slabs": [
            {"weight_from": 0, "weight_to": 500, "rate_per_kg": 2, "min_amount": 1000},
            {"weight_from": 500, "weight_to": 9999999999, "rate_per_kg": 2, "min_amount": 1000},
        ],
        "source_zone": "N1",
    }

    existing_profile = conn.execute(
        sa.text("SELECT courier_id FROM courier_rate_profiles WHERE courier_id = :cid"), {"cid": courier_id}
    ).fetchone()
    if existing_profile is None:
        conn.execute(
            sa.text(
                "INSERT INTO courier_rate_profiles (courier_id, profile_json, created_at, updated_at) "
                "VALUES (:cid, :profile, NOW(), NOW())"
            ),
            {"cid": courier_id, "profile": json.dumps(profile)},
        )


def downgrade() -> None:
    op.drop_table("courier_rate_profiles")
