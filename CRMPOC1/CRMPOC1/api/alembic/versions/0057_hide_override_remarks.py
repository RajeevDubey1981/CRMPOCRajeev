"""Bid history: take override and release remarks away from the vendor.

Before this, the line written when an admin overrode a bid (the old bidder's name and the reason) and the reason typed
when the bid team released a bid were visible to the vendor the bid went to. They are internal. This turns each of
them into a plain line for the vendor and keeps the full text for the bid team only (no vendor on it).

Revision ID: 0057_hide_override_remarks
Revises: 0056_bid_lines
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "0057_hide_override_remarks"
down_revision: Union[str, None] = "0056_bid_lines"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

INSERT = sa.text(
    "INSERT INTO bid_events (bid_id, at, actor_name, actor_user_id, action, text, vendor_id) "
    "VALUES (:bid_id, :at, :actor_name, :actor_user_id, :action, :text, NULL)"
)


def upgrade() -> None:
    bind = op.get_bind()
    if "bid_events" not in sa.inspect(bind).get_table_names():
        return
    names = {r[0]: r[1] for r in bind.execute(sa.text("SELECT id, name_of_firm FROM vendors"))}

    rows = bind.execute(sa.text(
        "SELECT id, bid_id, at, actor_name, actor_user_id, text, vendor_id FROM bid_events "
        "WHERE action = 'override' AND vendor_id IS NOT NULL"
    )).fetchall()
    for row in rows:
        full = row[5]
        cut = full.find(". Confirm by")
        tail = full[cut:] if cut >= 0 else ""
        plain = f"Allocated to {names.get(row[6], 'the bidder')}{tail}"
        bind.execute(INSERT, {"bid_id": row[1], "at": row[2], "actor_name": row[3], "actor_user_id": row[4], "action": "override", "text": full})
        bind.execute(sa.text("UPDATE bid_events SET action = 'allocated', text = :t WHERE id = :i"), {"t": plain, "i": row[0]})

    rows = bind.execute(sa.text(
        "SELECT id, bid_id, at, actor_name, actor_user_id, text FROM bid_events "
        "WHERE action = 'released' AND vendor_id IS NOT NULL AND actor_user_id IS NOT NULL AND text NOT LIKE '% declined%' AND text NOT LIKE 'Released by INDcool%'"
    )).fetchall()
    for row in rows:
        bind.execute(INSERT, {"bid_id": row[1], "at": row[2], "actor_name": row[3], "actor_user_id": row[4], "action": "released", "text": row[5]})
        bind.execute(
            sa.text("UPDATE bid_events SET text = 'Released by INDcool. The bid is free for allocation again' WHERE id = :i"),
            {"i": row[0]},
        )

    for row in bind.execute(sa.text("SELECT id, vendor_id FROM bid_events WHERE action = 'taken_back' AND vendor_id IS NOT NULL")).fetchall():
        bind.execute(sa.text("UPDATE bid_events SET text = 'Taken back by INDcool' WHERE id = :i"), {"i": row[0]})


def downgrade() -> None:
    pass
