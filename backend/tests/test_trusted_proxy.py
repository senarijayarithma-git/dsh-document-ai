import asyncio

from uvicorn.middleware.proxy_headers import ProxyHeadersMiddleware


def test_untrusted_peer_cannot_spoof_client_ip():
    observed = {}

    async def app(scope, receive, send):
        observed["client"] = scope["client"]

    middleware = ProxyHeadersMiddleware(
        app,
        trusted_hosts=["127.0.0.1"],
    )

    scope = {
        "type": "http",
        "client": ("203.0.113.10", 50000),
        "scheme": "http",
        "headers": [
            (b"x-forwarded-for", b"198.51.100.25"),
        ],
    }

    asyncio.run(middleware(scope, None, None))

    assert observed["client"][0] == "203.0.113.10"


def test_trusted_peer_uses_forwarded_client_ip():
    observed = {}

    async def app(scope, receive, send):
        observed["client"] = scope["client"]

    middleware = ProxyHeadersMiddleware(
        app,
        trusted_hosts=["127.0.0.1"],
    )

    scope = {
        "type": "http",
        "client": ("127.0.0.1", 50000),
        "scheme": "http",
        "headers": [
            (b"x-forwarded-for", b"198.51.100.25"),
        ],
    }

    asyncio.run(middleware(scope, None, None))

    assert observed["client"][0] == "198.51.100.25"
