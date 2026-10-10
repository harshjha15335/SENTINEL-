from sqlalchemy import create_engine

import app.models  # noqa: F401  (registers tables)
from alembic import context
from app.core.config import get_settings
from app.db.base import Base

target_metadata = Base.metadata


def run() -> None:
    url = context.config.attributes.get("database_url") or get_settings().database_url
    if context.is_offline_mode():
        context.configure(url=url, target_metadata=target_metadata, literal_binds=True)
        with context.begin_transaction():
            context.run_migrations()
        return
    engine = create_engine(url)
    with engine.connect() as conn:
        context.configure(connection=conn, target_metadata=target_metadata, compare_type=True)
        with context.begin_transaction():
            context.run_migrations()


run()
