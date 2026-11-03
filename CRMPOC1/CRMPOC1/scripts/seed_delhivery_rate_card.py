"""One-off: write Delhivery's B2B agreement rate card (zone matrix + overheads, from
"Agreement For INDCOOL ELECTRICALS PVT. LTD. - B2B") onto the courier named "Delhivery Limited",
and soft-delete the duplicate courier named "Delhivery" so orders aren't split across two records.

Runs on the production server over the same SSH connection scripts/deploy.py uses, so it reads the
real DB credentials from the server's own .env -- nothing is read or typed locally.

Usage (from project root):
  py scripts/seed_delhivery_rate_card.py
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from deploy import load_config, ssh_run  # noqa: E402

import paramiko  # noqa: E402

REMOTE_SCRIPT = r"""
import json, os, sys
from pathlib import Path

sys.path.insert(0, "/var/www/indcool/api")

for line in Path("/var/www/indcool/api/.env").read_text(encoding="utf-8").splitlines():
    line = line.strip()
    if not line or line.startswith("#") or "=" not in line:
        continue
    k, v = line.split("=", 1)
    os.environ[k.strip()] = v.strip()
os.chdir("/var/www/indcool/api")

from app.database import SessionLocal
from app.models.courier import Courier
from app.models.courier_rate_profile import CourierRateProfile
from sqlalchemy import select
from datetime import datetime, timezone

PROFILE = {
    "zones": ["N1", "N2", "E", "NE", "W1", "W2", "S1", "S2", "Central"],
    "zone_states": {
        "N1": ["Delhi", "Uttar Pradesh", "Haryana", "Rajasthan"],
        "N2": ["Chandigarh", "Punjab", "Himachal Pradesh", "Uttarakhand", "Jammu and Kashmir", "Ladakh"],
        "E": ["West Bengal", "Odisha", "Bihar", "Jharkhand"],
        "NE": ["Assam", "Meghalaya", "Tripura", "Arunachal Pradesh", "Mizoram", "Manipur", "Nagaland", "Sikkim"],
        "W1": ["Gujarat", "Daman and Diu", "Dadra and Nagar Haveli"],
        "W2": ["Maharashtra", "Goa"],
        "S1": ["Andhra Pradesh", "Telangana", "Karnataka", "Tamil Nadu", "Puducherry"],
        "S2": ["Kerala"],
        "Central": ["Madhya Pradesh", "Chhattisgarh"],
    },
    "zone_rates": [
        {"from_zone": "N1", "to_zone": "N1", "rate_per_kg": 5.92},
        {"from_zone": "N1", "to_zone": "N2", "rate_per_kg": 6.41},
        {"from_zone": "N1", "to_zone": "E", "rate_per_kg": 12.31},
        {"from_zone": "N1", "to_zone": "NE", "rate_per_kg": 22.55},
        {"from_zone": "N1", "to_zone": "W1", "rate_per_kg": 7.65},
        {"from_zone": "N1", "to_zone": "W2", "rate_per_kg": 10.75},
        {"from_zone": "N1", "to_zone": "S1", "rate_per_kg": 14.42},
        {"from_zone": "N1", "to_zone": "S2", "rate_per_kg": 18.40},
        {"from_zone": "N1", "to_zone": "Central", "rate_per_kg": 10.06},

        {"from_zone": "N2", "to_zone": "N1", "rate_per_kg": 7.67},
        {"from_zone": "N2", "to_zone": "N2", "rate_per_kg": 7.27},
        {"from_zone": "N2", "to_zone": "E", "rate_per_kg": 15.62},
        {"from_zone": "N2", "to_zone": "NE", "rate_per_kg": 23.76},
        {"from_zone": "N2", "to_zone": "W1", "rate_per_kg": 11.46},
        {"from_zone": "N2", "to_zone": "W2", "rate_per_kg": 12.95},
        {"from_zone": "N2", "to_zone": "S1", "rate_per_kg": 18.49},
        {"from_zone": "N2", "to_zone": "S2", "rate_per_kg": 23.05},
        {"from_zone": "N2", "to_zone": "Central", "rate_per_kg": 12.50},

        {"from_zone": "E", "to_zone": "N1", "rate_per_kg": 9.11},
        {"from_zone": "E", "to_zone": "N2", "rate_per_kg": 10.67},
        {"from_zone": "E", "to_zone": "E", "rate_per_kg": 8.03},
        {"from_zone": "E", "to_zone": "NE", "rate_per_kg": 13.94},
        {"from_zone": "E", "to_zone": "W1", "rate_per_kg": 9.94},
        {"from_zone": "E", "to_zone": "W2", "rate_per_kg": 9.12},
        {"from_zone": "E", "to_zone": "S1", "rate_per_kg": 11.57},
        {"from_zone": "E", "to_zone": "S2", "rate_per_kg": 15.14},
        {"from_zone": "E", "to_zone": "Central", "rate_per_kg": 8.43},

        {"from_zone": "NE", "to_zone": "N1", "rate_per_kg": 7.16},
        {"from_zone": "NE", "to_zone": "N2", "rate_per_kg": 10.32},
        {"from_zone": "NE", "to_zone": "E", "rate_per_kg": 7.34},
        {"from_zone": "NE", "to_zone": "NE", "rate_per_kg": 11.31},
        {"from_zone": "NE", "to_zone": "W1", "rate_per_kg": 8.29},
        {"from_zone": "NE", "to_zone": "W2", "rate_per_kg": 10.14},
        {"from_zone": "NE", "to_zone": "S1", "rate_per_kg": 12.22},
        {"from_zone": "NE", "to_zone": "S2", "rate_per_kg": 11.21},
        {"from_zone": "NE", "to_zone": "Central", "rate_per_kg": 8.35},

        {"from_zone": "W1", "to_zone": "N1", "rate_per_kg": 11.08},
        {"from_zone": "W1", "to_zone": "N2", "rate_per_kg": 11.05},
        {"from_zone": "W1", "to_zone": "E", "rate_per_kg": 18.21},
        {"from_zone": "W1", "to_zone": "NE", "rate_per_kg": 28.95},
        {"from_zone": "W1", "to_zone": "W1", "rate_per_kg": 6.83},
        {"from_zone": "W1", "to_zone": "W2", "rate_per_kg": 9.75},
        {"from_zone": "W1", "to_zone": "S1", "rate_per_kg": 15.39},
        {"from_zone": "W1", "to_zone": "S2", "rate_per_kg": 18.64},
        {"from_zone": "W1", "to_zone": "Central", "rate_per_kg": 10.64},

        {"from_zone": "W2", "to_zone": "N1", "rate_per_kg": 11.19},
        {"from_zone": "W2", "to_zone": "N2", "rate_per_kg": 13.66},
        {"from_zone": "W2", "to_zone": "E", "rate_per_kg": 17.05},
        {"from_zone": "W2", "to_zone": "NE", "rate_per_kg": 26.37},
        {"from_zone": "W2", "to_zone": "W1", "rate_per_kg": 8.83},
        {"from_zone": "W2", "to_zone": "W2", "rate_per_kg": 7.96},
        {"from_zone": "W2", "to_zone": "S1", "rate_per_kg": 11.84},
        {"from_zone": "W2", "to_zone": "S2", "rate_per_kg": 15.12},
        {"from_zone": "W2", "to_zone": "Central", "rate_per_kg": 10.35},

        {"from_zone": "S1", "to_zone": "N1", "rate_per_kg": 11.72},
        {"from_zone": "S1", "to_zone": "N2", "rate_per_kg": 13.37},
        {"from_zone": "S1", "to_zone": "E", "rate_per_kg": 14.26},
        {"from_zone": "S1", "to_zone": "NE", "rate_per_kg": 22.73},
        {"from_zone": "S1", "to_zone": "W1", "rate_per_kg": 9.53},
        {"from_zone": "S1", "to_zone": "W2", "rate_per_kg": 7.76},
        {"from_zone": "S1", "to_zone": "S1", "rate_per_kg": 8.73},
        {"from_zone": "S1", "to_zone": "S2", "rate_per_kg": 9.58},
        {"from_zone": "S1", "to_zone": "Central", "rate_per_kg": 11.28},

        {"from_zone": "S2", "to_zone": "N1", "rate_per_kg": 12.73},
        {"from_zone": "S2", "to_zone": "N2", "rate_per_kg": 15.38},
        {"from_zone": "S2", "to_zone": "E", "rate_per_kg": 17.23},
        {"from_zone": "S2", "to_zone": "NE", "rate_per_kg": 25.95},
        {"from_zone": "S2", "to_zone": "W1", "rate_per_kg": 10.06},
        {"from_zone": "S2", "to_zone": "W2", "rate_per_kg": 8.51},
        {"from_zone": "S2", "to_zone": "S1", "rate_per_kg": 7.51},
        {"from_zone": "S2", "to_zone": "S2", "rate_per_kg": 6.87},
        {"from_zone": "S2", "to_zone": "Central", "rate_per_kg": 12.06},

        {"from_zone": "Central", "to_zone": "N1", "rate_per_kg": 7.78},
        {"from_zone": "Central", "to_zone": "N2", "rate_per_kg": 9.57},
        {"from_zone": "Central", "to_zone": "E", "rate_per_kg": 12.37},
        {"from_zone": "Central", "to_zone": "NE", "rate_per_kg": 21.51},
        {"from_zone": "Central", "to_zone": "W1", "rate_per_kg": 6.33},
        {"from_zone": "Central", "to_zone": "W2", "rate_per_kg": 6.94},
        {"from_zone": "Central", "to_zone": "S1", "rate_per_kg": 13.20},
        {"from_zone": "Central", "to_zone": "S2", "rate_per_kg": 16.63},
        {"from_zone": "Central", "to_zone": "Central", "rate_per_kg": 8.87},
    ],
    "docket_charge": 200.0,
    "fsc_percent": 20.0,
    "volumetric_divisor": 4500.0,
    "handling_rate_per_kg": 3.0,
    "handling_min_weight_kg": 400.0,
    "demurrage_rate_per_kg": 1.0,
    "demurrage_min_amount": 100.0,
    "free_storage_days": 4,
    "min_chargeable_weight_kg": 0.0,
    "min_chargeable_amount": 0.0,
    "base_diesel_rate": 98.13,
    # Agreement: 0.40% freight change per Rs 1 change in diesel, applied at Mumbai/Chennai/Delhi/Kolkata.
    "fuel_hike_percent_per_rupee": 0.40,
    "oda_slabs": [],
    # Registered address on the agreement is Noida, Uttar Pradesh (zone N1) -- confirm/correct this
    # if shipments actually originate from a different warehouse.
    "source_zone": "N1",
}

db = SessionLocal()
try:
    target = db.scalar(select(Courier).where(Courier.courier_name == "Delhivery Limited", Courier.deleted_at.is_(None)))
    duplicate = db.scalar(select(Courier).where(Courier.courier_name == "Delhivery", Courier.deleted_at.is_(None)))

    if target is None:
        print("!!! No active courier named exactly 'Delhivery Limited' found -- nothing written.")
        raise SystemExit(1)

    row = db.scalar(select(CourierRateProfile).where(CourierRateProfile.courier_id == target.id))
    if row is None:
        row = CourierRateProfile(courier_id=target.id, profile_json=json.dumps(PROFILE))
        db.add(row)
        print(f"Created rate profile for Delhivery Limited (courier_id={target.id})")
    else:
        row.profile_json = json.dumps(PROFILE)
        print(f"Updated existing rate profile for Delhivery Limited (courier_id={target.id})")

    if duplicate is not None:
        duplicate.deleted_at = datetime.now(timezone.utc)
        print(f"Soft-deleted duplicate courier 'Delhivery' (courier_id={duplicate.id})")
    else:
        print("No separate 'Delhivery' courier found to disable (nothing to do there).")

    db.commit()
    print("Done.")
finally:
    db.close()
"""


def main() -> int:
    config = load_config()
    host = config["INDCOOL_DEPLOY_HOST"]
    user = config["INDCOOL_DEPLOY_USER"]
    password = config.get("INDCOOL_DEPLOY_PASSWORD") or None
    key_filename = config.get("INDCOOL_DEPLOY_KEY_FILENAME") or None
    remote_api = config["REMOTE_API"]

    if not password and not key_filename:
        print(f"Production deploy SSH authentication is not configured in scripts/deploy.env.")
        return 1

    client = paramiko.SSHClient()
    client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    print(f"Connecting to {host} as {user}...")
    ssh_options = {"username": user, "timeout": 30, "allow_agent": True, "look_for_keys": True}
    if password:
        ssh_options["password"] = password
    if key_filename:
        ssh_options["key_filename"] = key_filename
    client.connect(host, **ssh_options)
    try:
        remote = REMOTE_SCRIPT.replace("/var/www/indcool/api", remote_api)
        ssh_run(client, f"cat > /tmp/indcool_seed_delhivery.py <<'PY'\n{remote}\nPY")
        print(ssh_run(client, f"sudo -u www-data {remote_api}/venv/bin/python /tmp/indcool_seed_delhivery.py"))
    finally:
        client.close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
