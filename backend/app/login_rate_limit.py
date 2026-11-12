import os
import time
from collections import deque
from math import ceil
from threading import Lock

from fastapi import HTTPException, Request, status


_attempts = {}
_lock = Lock()


def _positive_int(name: str, default: int) -> int:
    try:
        value = int(os.getenv(name, str(default)))
    except ValueError as exc:
        raise RuntimeError(f"{name} must be an integer.") from exc

    if value < 1:
        raise RuntimeError(f"{name} must be positive.")

    return value


def _reject(retry_after: int) -> None:
    raise HTTPException(
        status_code=status.HTTP_429_TOO_MANY_REQUESTS,
        detail="Too many login attempts. Please try again later.",
        headers={"Retry-After": str(max(1, retry_after))},
    )


def check_login_rate_limit(request: Request) -> None:
    limit = _positive_int("LOGIN_RATE_LIMIT_ATTEMPTS", 5)
    window = _positive_int("LOGIN_RATE_LIMIT_WINDOW_SECONDS", 60)
    max_clients = _positive_int("LOGIN_RATE_LIMIT_MAX_CLIENTS", 10000)

    # Use the direct connection IP, not untrusted forwarding headers.
    client_ip = request.client.host if request.client else "unknown"
    now = time.monotonic()

    with _lock:
        timestamps = _attempts.get(client_ip)

        if timestamps is None:
            if len(_attempts) >= max_clients:
                # Reclaim expired clients only when capacity is reached.
                for key, recorded in list(_attempts.items()):
                    while recorded and now - recorded[0] >= window:
                        recorded.popleft()

                    if not recorded:
                        del _attempts[key]

            if len(_attempts) >= max_clients:
                # Preserve active records instead of evicting them.
                earliest_expiry = min(
                    recorded[0] + window
                    for recorded in _attempts.values()
                )
                _reject(ceil(earliest_expiry - now))

            timestamps = deque()
            _attempts[client_ip] = timestamps

        while timestamps and now - timestamps[0] >= window:
            timestamps.popleft()

        if len(timestamps) >= limit:
            _reject(ceil(window - (now - timestamps[0])))

        timestamps.append(now)
