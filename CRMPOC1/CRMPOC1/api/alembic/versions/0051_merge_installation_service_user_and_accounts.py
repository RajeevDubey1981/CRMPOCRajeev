"""Join the installation service-user branch and the accounts branch into one line.

The live database was already stamped with this revision name by an earlier deploy, so the file has to exist under
exactly this name or "alembic upgrade head" cannot find where the database is. It changes no tables.

Revision ID: 0051_merge_installation_service_user_and_accounts
Revises: 0047_installation_service_user_assignment, 0050_accounts_purchase_bom
"""

from typing import Sequence, Union

revision: str = "0051_merge_installation_service_user_and_accounts"
down_revision: Union[str, Sequence[str], None] = (
    "0047_installation_service_user_assignment",
    "0050_accounts_purchase_bom",
)
branch_labels = None
depends_on = None


def upgrade() -> None:
    pass


def downgrade() -> None:
    pass
