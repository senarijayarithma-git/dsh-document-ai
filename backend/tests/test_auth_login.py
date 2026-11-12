from uuid import uuid4

import pytest

from app.auth_security import hash_password
from app.nmra_models import EmployeeUser
from app.login_rate_limit import _attempts, _lock


@pytest.fixture(autouse=True)
def reset_login_rate_limit():
    with _lock:
        _attempts.clear()

    yield

    with _lock:
        _attempts.clear()


def test_employee_can_login_with_valid_credentials(
    client,
    test_db,
    monkeypatch,
):
    monkeypatch.setenv(
        "JWT_SECRET_KEY",
        "dsh-login-test-secret-with-enough-entropy-2026",
    )

    email = f"login-{uuid4().hex}@example.com"
    password = "TestPassword123!"

    employee = EmployeeUser(
        email=email,
        full_name="Login Test Employee",
        password_hash=hash_password(password),
        role="ADMIN",
        is_active=True,
    )

    test_db.add(employee)
    test_db.flush()

    response = client.post(
        "/auth/login",
        json={
            "email": email,
            "password": password,
        },
    )

    assert response.status_code == 200, response.text
    assert response.json()["access_token"]


def test_employee_login_rejects_invalid_password(
    client,
    test_db,
):
    email = f"invalid-{uuid4().hex}@example.com"

    employee = EmployeeUser(
        email=email,
        full_name="Invalid Password Test",
        password_hash=hash_password("CorrectPassword123!"),
        role="ADMIN",
        is_active=True,
    )

    test_db.add(employee)
    test_db.flush()

    response = client.post(
        "/auth/login",
        json={
            "email": email,
            "password": "WrongPassword123!",
        },
    )

    assert response.status_code == 401
    assert response.json()["detail"] == (
        "Invalid email or password."
    )


def test_employee_login_rejects_inactive_employee(
    client,
    test_db,
):
    email = f"inactive-{uuid4().hex}@example.com"

    employee = EmployeeUser(
        email=email,
        full_name="Inactive Login Test",
        password_hash=hash_password("TestPassword123!"),
        role="VIEWER",
        is_active=False,
    )

    test_db.add(employee)
    test_db.flush()

    response = client.post(
        "/auth/login",
        json={
            "email": email,
            "password": "TestPassword123!",
        },
    )

    assert response.status_code == 401


def test_employee_login_rate_limit(
    client,
    monkeypatch,
):
    monkeypatch.setenv("LOGIN_RATE_LIMIT_ATTEMPTS", "3")
    monkeypatch.setenv("LOGIN_RATE_LIMIT_WINDOW_SECONDS", "60")

    email = f"rate-limit-{uuid4().hex}@example.com"

    responses = [
        client.post(
            "/auth/login",
            json={
                "email": email,
                "password": "WrongPassword123!",
            },
        )
        for _ in range(4)
    ]

    assert [response.status_code for response in responses] == [
        401,
        401,
        401,
        429,
    ]

    assert int(responses[-1].headers["Retry-After"]) > 0
