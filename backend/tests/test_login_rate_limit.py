from concurrent.futures import ThreadPoolExecutor
from threading import Barrier

import pytest
from fastapi import HTTPException
from starlette.requests import Request

from app import login_rate_limit


@pytest.fixture(autouse=True)
def reset_limiter():
    with login_rate_limit._lock:
        login_rate_limit._attempts.clear()

    yield

    with login_rate_limit._lock:
        login_rate_limit._attempts.clear()


def make_request(ip="192.0.2.10"):
    return Request({
        "type": "http",
        "method": "POST",
        "path": "/auth/login",
        "headers": [],
        "client": (ip, 12345),
    })


def test_rate_limit_expires(monkeypatch):
    monkeypatch.setenv("LOGIN_RATE_LIMIT_ATTEMPTS", "2")
    monkeypatch.setenv("LOGIN_RATE_LIMIT_WINDOW_SECONDS", "10")

    clock = [100.0]
    monkeypatch.setattr(
        login_rate_limit.time,
        "monotonic",
        lambda: clock[0],
    )

    request = make_request()

    login_rate_limit.check_login_rate_limit(request)
    login_rate_limit.check_login_rate_limit(request)

    with pytest.raises(HTTPException) as error:
        login_rate_limit.check_login_rate_limit(request)

    assert error.value.status_code == 429
    assert int(error.value.headers["Retry-After"]) > 0

    clock[0] = 111.0

    login_rate_limit.check_login_rate_limit(request)


def test_different_ips_have_separate_limits(monkeypatch):
    monkeypatch.setenv("LOGIN_RATE_LIMIT_ATTEMPTS", "1")
    monkeypatch.setenv("LOGIN_RATE_LIMIT_WINDOW_SECONDS", "60")

    login_rate_limit.check_login_rate_limit(
        make_request("192.0.2.10")
    )

    login_rate_limit.check_login_rate_limit(
        make_request("192.0.2.11")
    )

    with pytest.raises(HTTPException) as error:
        login_rate_limit.check_login_rate_limit(
            make_request("192.0.2.10")
        )

    assert error.value.status_code == 429


def test_concurrent_requests_respect_limit(monkeypatch):
    monkeypatch.setenv("LOGIN_RATE_LIMIT_ATTEMPTS", "3")
    monkeypatch.setenv("LOGIN_RATE_LIMIT_WINDOW_SECONDS", "60")

    barrier = Barrier(8)

    def attempt():
        barrier.wait()

        try:
            login_rate_limit.check_login_rate_limit(
                make_request("192.0.2.20")
            )
            return 200
        except HTTPException as error:
            return error.status_code

    with ThreadPoolExecutor(max_workers=8) as executor:
        results = list(executor.map(lambda _: attempt(), range(8)))

    assert results.count(200) == 3
    assert results.count(429) == 5


def test_limiter_bounds_tracked_clients(monkeypatch):
    monkeypatch.setenv("LOGIN_RATE_LIMIT_ATTEMPTS", "3")
    monkeypatch.setenv("LOGIN_RATE_LIMIT_WINDOW_SECONDS", "60")
    monkeypatch.setenv("LOGIN_RATE_LIMIT_MAX_CLIENTS", "2")

    for ip in (
        "192.0.2.10",
        "192.0.2.11",
    ):
        login_rate_limit.check_login_rate_limit(
            make_request(ip)
        )

    with pytest.raises(HTTPException) as error:
        login_rate_limit.check_login_rate_limit(
            make_request("192.0.2.12")
        )

    assert error.value.status_code == 429
    assert int(error.value.headers["Retry-After"]) > 0
    assert len(login_rate_limit._attempts) == 2


def test_expired_clients_free_capacity(monkeypatch):
    monkeypatch.setenv("LOGIN_RATE_LIMIT_ATTEMPTS", "2")
    monkeypatch.setenv("LOGIN_RATE_LIMIT_WINDOW_SECONDS", "10")
    monkeypatch.setenv("LOGIN_RATE_LIMIT_MAX_CLIENTS", "2")

    clock = [100.0]
    monkeypatch.setattr(
        login_rate_limit.time,
        "monotonic",
        lambda: clock[0],
    )

    login_rate_limit.check_login_rate_limit(
        make_request("192.0.2.10")
    )
    login_rate_limit.check_login_rate_limit(
        make_request("192.0.2.11")
    )

    with pytest.raises(HTTPException) as error:
        login_rate_limit.check_login_rate_limit(
            make_request("192.0.2.12")
        )

    assert error.value.status_code == 429

    clock[0] = 111.0

    login_rate_limit.check_login_rate_limit(
        make_request("192.0.2.12")
    )

    assert len(login_rate_limit._attempts) <= 2
    assert "192.0.2.12" in login_rate_limit._attempts
