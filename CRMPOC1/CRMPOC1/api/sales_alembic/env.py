"""Updates for the Sales database only. The CRM database has its own folder (alembic/)."""

from logging.config import fileConfig

from alembic import context
from sqlalchemy import create_engine, pool

from app.config import settings
from app.sales import models  # noqa: F401 - registers the Sales tables
from app.sales.db import SalesBase

config = context.config
url = (settings.sales_database_url or "").strip()
if not url:
    raise SystemExit("SALES_DATABASE_URL is empty: the Sales database is not set up, so there is nothing to update.")

if config.config_file_name is not None:
    fileConfig(config.config_file_name)

target_metadata = SalesBase.metadata
VERSION_TABLE = "sales_alembic_version"


def run_migrations_offline() -> None:
    context.configure(url=url, target_metadata=target_metadata, literal_binds=True, version_table=VERSION_TABLE,
                      dialect_opts={"paramstyle": "named"})
    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    connectable = create_engine(url, poolclass=pool.NullPool)
    with connectable.connect() as connection:
        context.configure(connection=connection, target_metadata=target_metadata, version_table=VERSION_TABLE)
        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
