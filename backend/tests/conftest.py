
import os
from pathlib import Path

from sqlalchemy.engine import make_url


# Locate backend/.env.test
BACKEND_DIR = Path(__file__).resolve().parent.parent
TEST_ENV_FILE = BACKEND_DIR / ".env.test"

EXPECTED_TEST_DATABASE = "dsh_document_ai_test"


def load_test_database_url():
    if not TEST_ENV_FILE.exists():
        raise RuntimeError(
            "SAFETY STOP: backend/.env.test is missing."
        )

    values = []

    for line in TEST_ENV_FILE.read_text(encoding="utf-8").splitlines():
        line = line.strip()

        if line.startswith("DATABASE_URL="):
            values.append(line.split("=", 1)[1].strip())

    if len(values) != 1:
        raise RuntimeError(
            "SAFETY STOP: Expected exactly one DATABASE_URL in .env.test."
        )

    database_url = values[0]
    parsed_url = make_url(database_url)

    if (
        parsed_url.get_backend_name() != "postgresql"
        or parsed_url.database != EXPECTED_TEST_DATABASE
    ):
        raise RuntimeError(
            "SAFETY STOP: Refusing to use a database other than "
            "dsh_document_ai_test."
        )

    return database_url


# Configure the test database before importing application modules.
os.environ["DATABASE_URL"] = load_test_database_url()

import pytest
from sqlalchemy import create_engine, text


@pytest.fixture(scope="session")
def verified_test_engine():
    """
    Connect to PostgreSQL and verify the actual database
    before allowing tests to use this engine.
    """
    database_url = load_test_database_url()

    engine = create_engine(database_url, pool_pre_ping=True)

    try:
        with engine.connect() as connection:
            actual_database = connection.execute(
                text("SELECT current_database()")
            ).scalar_one()

            if actual_database != EXPECTED_TEST_DATABASE:
                raise RuntimeError(
                    "SAFETY STOP: PostgreSQL connected to "
                    f"{actual_database!r}, not "
                    f"{EXPECTED_TEST_DATABASE!r}."
                )


        # Import only the document table needed by business API tests.
        from app.db_models import Document

        # Verify the database again before changing its schema.
        with engine.begin() as connection:
            actual_database = connection.execute(
                text("SELECT current_database()")
            ).scalar_one()

            if actual_database != EXPECTED_TEST_DATABASE:
                raise RuntimeError(
                    "SAFETY STOP: Schema initialization refused "
                    f"for database {actual_database!r}."
                )

            # Create the documents table only if it does not exist.
            Document.__table__.create(
                bind=connection,
                checkfirst=True,
            )

        print(
            "\nSAFETY CHECK PASSED: Connected to "
            "dsh_document_ai_test."
        )
        print(
            "TEST SCHEMA READY: documents table verified."
        )

        yield engine

    finally:
        engine.dispose()

from sqlalchemy.orm import Session


@pytest.fixture
def test_db(verified_test_engine):
    """
    Give each test an isolated database session.

    Even if application code calls db.commit(),
    the outer transaction is rolled back afterward.
    """
    connection = verified_test_engine.connect()

    transaction = connection.begin()

    session = Session(
        bind=connection,
        autoflush=False,
        expire_on_commit=False,
        join_transaction_mode="create_savepoint",
    )

    try:
        yield session
    finally:
        session.close()
        transaction.rollback()
        connection.close()

from fastapi.testclient import TestClient


@pytest.fixture
def client(test_db):
    from app.main import app
    from app.database import get_db

    def override_get_db():
        yield test_db

    app.dependency_overrides[get_db] = override_get_db

    try:
        with TestClient(app) as test_client:
            yield test_client
    finally:
        app.dependency_overrides.pop(get_db, None)

@pytest.fixture
def legacy_authenticated_client():
    """
    Authenticated TestClient for older business-logic tests.

    Authentication is bypassed ONLY inside this test fixture.
    Production authentication remains unchanged.
    """
    from fastapi.testclient import TestClient

    from app.main import app
    from app.auth_dependencies import get_current_employee
    from app.nmra_models import EmployeeUser

    test_employee = EmployeeUser(
        id=999999,
        email="legacy-test@example.com",
        full_name="Legacy Test Employee",
        role="ADMIN",
        is_active=True,
        password_hash="test-only-not-a-real-password",
    )

    previous_override = app.dependency_overrides.get(
        get_current_employee
    )

    app.dependency_overrides[get_current_employee] = (
        lambda: test_employee
    )

    try:
        with TestClient(app) as test_client:
            yield test_client
    finally:
        if previous_override is None:
            app.dependency_overrides.pop(
                get_current_employee,
                None,
            )
        else:
            app.dependency_overrides[
                get_current_employee
            ] = previous_override
