import pytest

from app.auth_security import get_jwt_secret


def test_missing_jwt_secret_rejected(monkeypatch):
    monkeypatch.delenv("JWT_SECRET_KEY", raising=False)

    with pytest.raises(RuntimeError):
        get_jwt_secret()


def test_short_jwt_secret_rejected(monkeypatch):
    monkeypatch.setenv("JWT_SECRET_KEY", "short")

    with pytest.raises(RuntimeError):
        get_jwt_secret()


def test_production_placeholder_rejected(monkeypatch):
    monkeypatch.setenv("APP_ENV", "production")
    monkeypatch.setenv(
        "JWT_SECRET_KEY",
        "REPLACE_WITH_A_RANDOM_SECRET_OF_AT_LEAST_32_CHARACTERS",
    )

    with pytest.raises(RuntimeError):
        get_jwt_secret()


def test_production_repeated_secret_rejected(monkeypatch):
    monkeypatch.setenv("APP_ENV", "production")
    monkeypatch.setenv("JWT_SECRET_KEY", "a" * 64)

    with pytest.raises(RuntimeError):
        get_jwt_secret()


def test_production_valid_secret_accepted(monkeypatch):
    secret = "X9!k2@Lm7#Pq4$Rt8%Uv3&Wx6*Yz1+Ab5"

    monkeypatch.setenv("APP_ENV", "production")
    monkeypatch.setenv("JWT_SECRET_KEY", secret)

    assert get_jwt_secret() == secret
