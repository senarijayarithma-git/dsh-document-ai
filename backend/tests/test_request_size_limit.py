import json

import pytest

from app.request_size_limit import ShipmentRequestSizeLimitMiddleware
from fastapi import FastAPI, File, UploadFile
from fastapi.testclient import TestClient

SHIPMENT_PATH = "/shipments/upload-and-verify"


async def run_request(
    *,
    path=SHIPMENT_PATH,
    method="POST",
    headers=None,
    chunks=None,
    max_bytes=32 * 1024 * 1024,
):
    app_called = False
    sent_messages = []

    async def downstream_app(scope, receive, send):
        nonlocal app_called
        app_called = True

        while True:
            message = await receive()

            if message["type"] == "http.disconnect":
                break

            if message["type"] == "http.request":
                if not message.get("more_body", False):
                    break

        await send({
            "type": "http.response.start",
            "status": 200,
            "headers": [],
        })
        await send({
            "type": "http.response.body",
            "body": b"OK",
        })

    middleware = ShipmentRequestSizeLimitMiddleware(downstream_app)
    middleware.MAX_REQUEST_BYTES = max_bytes

    scope = {
        "type": "http",
        "method": method,
        "path": path,
        "headers": headers or [],
    }

    body_chunks = chunks if chunks is not None else [b""]
    messages = [
        {
            "type": "http.request",
            "body": chunk,
            "more_body": index < len(body_chunks) - 1,
        }
        for index, chunk in enumerate(body_chunks)
    ]

    async def receive():
        if messages:
            return messages.pop(0)

        return {"type": "http.disconnect"}

    async def send(message):
        sent_messages.append(message)

    await middleware(scope, receive, send)

    status = next(
        message["status"]
        for message in sent_messages
        if message["type"] == "http.response.start"
    )

    return status, app_called, sent_messages


@pytest.mark.asyncio
async def test_rejects_oversized_content_length():
    status, app_called, messages = await run_request(
        headers=[(b"content-length", b"101")],
        max_bytes=100,
    )

    assert status == 413
    assert app_called is False

    body = next(
        message["body"]
        for message in messages
        if message["type"] == "http.response.body"
    )

    assert "32 MiB" in json.loads(body)["detail"]


@pytest.mark.asyncio
async def test_rejects_invalid_content_length():
    status, app_called, _ = await run_request(
        headers=[(b"content-length", b"invalid")],
        max_bytes=100,
    )

    assert status == 400
    assert app_called is False


@pytest.mark.asyncio
async def test_rejects_negative_content_length():
    status, app_called, _ = await run_request(
        headers=[(b"content-length", b"-1")],
        max_bytes=100,
    )

    assert status == 400
    assert app_called is False


@pytest.mark.asyncio
async def test_rejects_streamed_body_over_limit():
    status, app_called, _ = await run_request(
        chunks=[b"a" * 60, b"b" * 41],
        max_bytes=100,
    )

    assert status == 413
    assert app_called is True


@pytest.mark.asyncio
async def test_accepts_body_exactly_at_limit():
    status, app_called, _ = await run_request(
        chunks=[b"a" * 60, b"b" * 40],
        max_bytes=100,
    )

    assert status == 200
    assert app_called is True


@pytest.mark.asyncio
async def test_other_routes_are_unaffected():
    status, app_called, _ = await run_request(
        path="/health",
        chunks=[b"a" * 101],
        max_bytes=100,
    )

    assert status == 200
    assert app_called is True


@pytest.mark.asyncio
async def test_other_methods_are_unaffected():
    status, app_called, _ = await run_request(
        method="GET",
        chunks=[b"a" * 101],
        max_bytes=100,
    )

    assert status == 200
    assert app_called is True

def test_real_multipart_request_exceeds_streamed_limit():
    class SmallLimitMiddleware(ShipmentRequestSizeLimitMiddleware):
        MAX_REQUEST_BYTES = 100

    test_app = FastAPI()
    test_app.add_middleware(SmallLimitMiddleware)

    @test_app.post("/shipments/upload-and-verify")
    async def upload(file: UploadFile = File(...)):
        return {"filename": file.filename}

    client = TestClient(test_app)

    response = client.post(
        "/shipments/upload-and-verify",
        files={
            "file": (
                "large.pdf",
                b"%PDF-" + b"x" * 200,
                "application/pdf",
            )
        },
    )

    assert response.status_code == 413
