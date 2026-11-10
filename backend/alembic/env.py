
import os
from logging.config import fileConfig
from pathlib import Path

from alembic import context
from dotenv import dotenv_values
from sqlalchemy import create_engine, inspect, text
from sqlalchemy.engine import make_url
from sqlalchemy.pool import NullPool

from app.database import Base

# Register only the active application models.
import app.db_models  # noqa: F401
import app.nmra_models  # noqa: F401


config = context.config

if config.config_file_name is not None:
    fileConfig(config.config_file_name)

BACKEND_DIR = Path(__file__).resolve().parent.parent

EXPECTED_TABLES = {
    "documents",
    "employee_users",
    "nmra_registrations",
    "nmra_product_mappings",
    "nmra_attachments",
    "nmra_attachment_items",
    "nmra_item_review_audit",
}

DATABASE_MODES = {
    "test": {
        "env_file": BACKEND_DIR / ".env.test",
        "database": "dsh_document_ai_test",
    },
    "sandbox": {
        "env_file": BACKEND_DIR / ".env.migration",
        "database": "dsh_document_ai_migration_sandbox",
    },
}

target_metadata = Base.metadata


def get_database_settings():
    mode = os.environ.get("DSH_ALEMBIC_TARGET", "test")

    if mode not in DATABASE_MODES:
        raise RuntimeError(
            "STOP: Invalid DSH_ALEMBIC_TARGET. "
            "Allowed values: test, sandbox."
        )

    settings = DATABASE_MODES[mode]
    env_file = settings["env_file"]
    expected_database = settings["database"]

    if not env_file.is_file():
        raise RuntimeError(
            f"STOP: Missing configuration file: {env_file.name}"
        )

    database_url = dotenv_values(env_file).get("DATABASE_URL")

    if not database_url:
        raise RuntimeError(
            f"STOP: DATABASE_URL missing from {env_file.name}"
        )

    parsed_url = make_url(database_url)

    if (
        not parsed_url.drivername.startswith("postgresql")
        or parsed_url.database != expected_database
        or parsed_url.host != "127.0.0.1"
        or (parsed_url.port or 5432) != 5432
    ):
        raise RuntimeError(
            "STOP: Database configuration failed safety checks."
        )

    return mode, expected_database, database_url


def run_migrations_offline():
    raise RuntimeError(
        "STOP: Offline migrations are disabled."
    )


def run_migrations_online():
    mode, expected_database, database_url = (
        get_database_settings()
    )

    engine = create_engine(
        database_url,
        poolclass=NullPool,
        pool_pre_ping=True,
    )

    try:
        with engine.begin() as connection:
            actual_database = connection.execute(
                text("SELECT current_database()")
            ).scalar_one()

            if actual_database != expected_database:
                raise RuntimeError(
                    "STOP: Connected to an unexpected database."
                )

            existing_tables = set(
                inspect(connection).get_table_names(
                    schema="public"
                )
            )

            if mode == "test":
                if not EXPECTED_TABLES.issubset(existing_tables):
                    missing = EXPECTED_TABLES - existing_tables
                    raise RuntimeError(
                        "STOP: Test database is missing tables: "
                        f"{sorted(missing)}"
                    )

            elif mode == "sandbox":
                # Permit either a completely empty sandbox
                # or a previously migrated sandbox.
                allowed_tables = EXPECTED_TABLES | {
                    "alembic_version"
                }

                unexpected = existing_tables - allowed_tables

                if unexpected:
                    raise RuntimeError(
                        "STOP: Sandbox contains unexpected tables: "
                        f"{sorted(unexpected)}"
                    )

                if (
                    existing_tables
                    and not EXPECTED_TABLES.issubset(existing_tables)
                ):
                    raise RuntimeError(
                        "STOP: Sandbox has a partial schema."
                    )

            print(
                "ALEMBIC SAFETY CHECK PASSED: "
                f"mode={mode}, database={actual_database}"
            )

            context.configure(
                connection=connection,
                target_metadata=target_metadata,
                compare_type=True,
                include_schemas=False,
            )

            with context.begin_transaction():
                context.run_migrations()

    finally:
        engine.dispose()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
