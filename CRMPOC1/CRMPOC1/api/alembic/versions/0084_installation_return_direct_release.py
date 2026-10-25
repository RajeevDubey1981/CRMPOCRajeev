"""Close approved returns and release serials without a location-verification step."""
from alembic import op
import sqlalchemy as sa
revision = "0084_return_direct_release"
down_revision = "0083_order_installation_required"
branch_labels = None
depends_on = None

def upgrade():
    conn = op.get_bind()
    rows = conn.execute(sa.text("SELECT id, order_item_id, status FROM installation_requests WHERE status IN ('Returned - Location Not Verified', 'Return Location Verified') ORDER BY id")).mappings().all()
    for row in rows:
        # Only release the legacy quarantine. Never reset an item already reused by a newer request.
        conn.execute(sa.text("UPDATE order_items SET installation_status='Not Requested' WHERE id=:item_id AND installation_status='Returned - Location Not Verified'"), {"item_id": row['order_item_id']})
        conn.execute(sa.text("UPDATE installation_requests SET status='Return Approved - Closed' WHERE id=:id"), {"id": row['id']})
        conn.execute(sa.text("INSERT INTO installation_status_logs (installation_request_id, action, old_status, new_status, performed_role, remarks, created_at) VALUES (:id, 'Location Return Workflow Updated', :old_status, 'Return Approved - Closed', 'system', 'Separate location verification removed. Approved return closed; order serial released for a new request.', CURRENT_TIMESTAMP)"), {"id": row['id'], "old_status": row['status']})

def downgrade():
    # Historical return decisions must not be reversed or re-lock serials already reassigned.
    pass
