"""Join the two migration branches into one head.

One branch is the installation service-user assignment (0047_installation_service_user_assignment) and the other is
the chain that ends with the Store and Accounts removal (0051). Without this, "alembic upgrade head" stops with
"Multiple head revisions are present". It changes no tables.

Revision ID: 0052_merge_heads
Revises: 0051_remove_store_accounts, 0047_installation_service_user_assignment
"""

from typing import Sequence, Union

revision: str = "0052_merge_heads"
down_revision: Union[str, Sequence[str], None] = (
    "0051_remove_store_accounts",
    "0047_installation_service_user_assignment",
)
branch_labels = None
depends_on = None


def upgrade() -> None:
    pass


def downgrade() -> None:
    pass
