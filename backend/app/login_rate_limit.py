import os
import time
from collections import deque
from threading import Lock

from fastapi import HTTPException, Request, status


_attempts = {}
_lock = Lock()


def _positive_int(name: str, default: int) -> int:
    value = int(os.getenv(name, str(default)))
    if value < 1:
        raise RuntimeError(f"{name} must be positive.")
    return value


def check_login_rate_limit(request: Request) -> None:
    limit = _positive_int("LOGIN_RATE_LIMIT_ATTEMPTS", 5)
    window = _positive_int("LOGIN_RATE_LIMIT_WINDOW_SECONDS", 60)

    # Use the directly connected client address.
    # Do not trust user-supplied forwarding headers here.
    client_ip = request.client.host if request.client else "unknown"

    now = time.monotonic()

    with _lock:
        # Periodically remove expired entries to bound memory use.
        for key, timestamps in list(_attempts.items()):
            while timestamps and now - timestamps[0] >= window:
                timestamps.popleft()
            if not timestamps:
                del _attempts[key]

        timestamps = _attempts.setdefault(client_ip, deque())

        if len(timestamps) >= limit:
            retry_after = max(
                1,
                int(window - (now - timestamps[0])) + 1,
            )
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail="Too many login attempts. Please try again later.",
                headers={"Retry-After": str(retry_after)},
            )

        timestamps.append(now)
