from logging.config import fileConfig

import sqlalchemy as sa
from alembic import context
from sqlmodel import SQLModel

# Import all models here to ensure they are registered with SQLModel.metadata
from care_pilot.platform.persistence.engine import get_db_engine

# this is the Alembic Config object, which provides
# access to the values within the .ini file in use.
config = context.config

# Interpret the config file for Python logging.
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# Define naming convention for constraints (required for SQLite batch mode)
naming_convention = {
    "ix": "ix_%(column_0_label)s",
    "uq": "uq_%(table_name)s_%(column_0_name)s",
    "ck": "ck_%(table_name)s_%(constraint_name)s",
    "fk": "fk_%(table_name)s_%(column_0_name)s_%(referred_table_name)s",
    "pk": "pk_%(table_name)s"
}

# Set target metadata for autogenerate
target_metadata = SQLModel.metadata
target_metadata.naming_convention = naming_convention


def run_migrations_offline() -> None:
    """Run migrations in 'offline' mode."""
    # For offline mode, we need a URL. We'll try to get it from settings if not in config.
    url = config.get_main_option("sqlalchemy.url")
    if not url:
        from care_pilot.config.app import get_settings

        settings = get_settings()
        if settings.storage.app_data_backend == "postgresql":
            url = settings.storage.api_postgres_url
        else:
            url = f"sqlite:///{settings.storage.api_sqlite_db_path}"

    def include_object(_object, name, type_, _reflected, _compare_to):  # noqa: ANN001
        return not (type_ == "table" and name not in target_metadata.tables)

    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
        render_as_batch=True,  # Critical for SQLite ALTER support
        include_object=include_object,
    )

    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    """Run migrations in 'online' mode."""
    # Use our centralized engine factory
    connectable = get_db_engine()

    def include_object(_object, name, type_, _reflected, _compare_to):  # noqa: ANN001
        return not (type_ == "table" and name not in target_metadata.tables)

    with connectable.connect() as connection:
        # Disable FKs for SQLite batch mode to prevent IntegrityError during re-creation
        if connection.dialect.name == "sqlite":
            connection.execute(sa.text("PRAGMA foreign_keys=OFF"))

        context.configure(
            connection=connection,
            target_metadata=target_metadata,
            render_as_batch=True,  # Critical for SQLite ALTER support
            include_object=include_object,
        )

        with context.begin_transaction():
            context.run_migrations()

        # Re-enable FKs
        if connection.dialect.name == "sqlite":
            connection.execute(sa.text("PRAGMA foreign_keys=ON"))


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
