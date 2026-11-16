
from starlette.types import ASGIApp, Receive, Scope, Send


class ShipmentRequestSizeLimitMiddleware:
    """Limit total incoming request bytes for shipment uploads."""

    MAX_REQUEST_BYTES = 32 * 1024 * 1024
    SHIPMENT_PATH = "/shipments/upload-and-verify"

    def __init__(self, app: ASGIApp):
        self.app = app

    async def __call__(
        self,
        scope: Scope,
        receive: Receive,
        send: Send,
    ) -> None:
        if (
            scope["type"] != "http"
            or scope.get("path") != self.SHIPMENT_PATH
            or scope.get("method") != "POST"
        ):
            await self.app(scope, receive, send)
            return

        headers = dict(scope.get("headers", []))
        content_length = headers.get(b"content-length")

        if content_length is not None:
            try:
                declared_size = int(content_length)
            except ValueError:
                await self._reject(send, 400, "Invalid Content-Length")
                return

            if declared_size < 0:
                await self._reject(send, 400, "Invalid Content-Length")
                return

            if declared_size > self.MAX_REQUEST_BYTES:
                await self._reject(send, 413, "Shipment request exceeds 32 MiB limit")
                return

        received_bytes = 0
        rejected = False

        async def limited_receive():
            nonlocal received_bytes, rejected

            message = await receive()

            if message["type"] == "http.request":
                received_bytes += len(message.get("body", b""))

                if received_bytes > self.MAX_REQUEST_BYTES:
                    rejected = True
                    raise _ShipmentRequestTooLarge()

            return message

        response_started = False

        async def guarded_send(message):
            nonlocal response_started

            if message["type"] == "http.response.start":
                response_started = True

            await send(message)

        try:
            await self.app(scope, limited_receive, guarded_send)
        except _ShipmentRequestTooLarge:
            if not response_started:
                await self._reject(
                    send,
                    413,
                    "Shipment request exceeds 32 MiB limit",
                )
            else:
                raise

    @staticmethod
    async def _reject(send: Send, status: int, detail: str) -> None:
        import json

        body = json.dumps({"detail": detail}).encode("utf-8")

        await send(
            {
                "type": "http.response.start",
                "status": status,
                "headers": [
                    (b"content-type", b"application/json"),
                    (b"content-length", str(len(body)).encode("ascii")),
                ],
            }
        )

        await send(
            {
                "type": "http.response.body",
                "body": body,
            }
        )


class _ShipmentRequestTooLarge(Exception):
    pass
