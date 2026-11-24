import pytest

from app.deployment_config import get_cors_origins


def test_development_uses_localhost_defaults(monkeypatch):
    monkeypatch.setenv("APP_ENV", "development")
    monkeypatch.delenv("CORS_ORIGINS", raising=False)

    assert get_cors_origins() == [
        "http://localhost:5173",
        "http://127.0.0.1:5173",
        "http://localhost:5174",
        "http://127.0.0.1:5174",
    ]

def test_production_requires_origins(monkeypatch):
    monkeypatch.setenv("APP_ENV", "production")
    monkeypatch.delenv("CORS_ORIGINS", raising=False)

    with pytest.raises(RuntimeError):
        get_cors_origins()


@pytest.mark.parametrize(
    "origin",
    [
        "*",
        "http://example.com",
        "http://localhost:5173",
        "https://example.com/path",
        "https://*.example.com",
    ],
)
def test_production_rejects_unsafe_origins(monkeypatch, origin):
    monkeypatch.setenv("APP_ENV", "production")
    monkeypatch.setenv("CORS_ORIGINS", origin)

    with pytest.raises(RuntimeError):
        get_cors_origins()


def test_production_accepts_https_origin(monkeypatch):
    monkeypatch.setenv("APP_ENV", "production")
    monkeypatch.setenv(
        "CORS_ORIGINS",
        "https://app.example.com",
    )

    assert get_cors_origins() == [
        "https://app.example.com"
    ]


def test_invalid_app_environment_rejected(monkeypatch):
    monkeypatch.setenv("APP_ENV", "unknown")

    with pytest.raises(RuntimeError):
        get_cors_origins()
