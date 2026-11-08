"""Run manually written SQL migrations using the existing database settings."""

from alembic import context
from sqlalchemy import URL, create_engine
from sqlalchemy.pool import NullPool

from rag_workflow_lab.config import load_database_settings


settings = load_database_settings()
url = URL.create(
    "postgresql+psycopg",
    username=settings.user,
    password=settings.password,
    host=settings.host,
    port=settings.port,
    database=settings.dbname,
    query={"connect_timeout": str(settings.connect_timeout)},
)

if context.is_offline_mode():
    context.configure(url=url, literal_binds=True)
    with context.begin_transaction():
        context.run_migrations()
else:
    engine = create_engine(url, poolclass=NullPool, hide_parameters=True)
    with engine.connect() as connection:
        context.configure(connection=connection)
        with context.begin_transaction():
            context.run_migrations()
