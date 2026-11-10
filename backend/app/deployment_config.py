import os
from urllib.parse import urlsplit


DEFAULT_CORS_ORIGINS = (
    "http://localhost:5173,"
    "http://127.0.0.1:5173"
)


def get_cors_origins() -> list[str]:
    app_env = os.getenv("APP_ENV", "development").strip().lower()

    if app_env not in {"development", "test", "production"}:
        raise RuntimeError(
            "APP_ENV must be development, test, or production."
        )

    configured = os.getenv("CORS_ORIGINS")

    if app_env == "production" and not configured:
        raise RuntimeError(
            "CORS_ORIGINS must be configured in production."
        )

    raw_origins = (
        configured
        if configured is not None
        else DEFAULT_CORS_ORIGINS
    )

    origins = [
        origin.strip().rstrip("/")
        for origin in raw_origins.split(",")
        if origin.strip()
    ]

    if app_env == "production":
        if not origins:
            raise RuntimeError(
                "Production CORS_ORIGINS cannot be empty."
            )

        for origin in origins:
            parsed = urlsplit(origin)

            if (
                parsed.scheme != "https"
                or not parsed.hostname
                or parsed.username is not None
                or parsed.password is not None
                or parsed.path not in ("", "/")
                or parsed.query
                or parsed.fragment
                or parsed.hostname.lower()
                in {"localhost", "127.0.0.1", "::1"}
                or "*" in origin
            ):
                raise RuntimeError(
                    "Production CORS origins must be explicit "
                    "HTTPS origins without paths, wildcards, "
                    "or localhost addresses."
                )

    return origins
