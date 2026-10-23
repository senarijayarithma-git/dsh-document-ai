
import asyncio
from unittest.mock import patch

from fastapi import HTTPException
from google.genai import errors

from app.main import StructuredExtractionRequest, extract_structured


def simulate_rate_limit(**kwargs):
    raise errors.ClientError(
        code=429,
        response_json={
            "error": {
                "code": 429,
                "message": "Rate limit exceeded",
                "status": "RESOURCE_EXHAUSTED",
            }
        },
    )


def test_gemini_rate_limit():
    payload = StructuredExtractionRequest(
        text="Invoice number INV-001",
        document_type="invoice",
    )

    with patch(
        "app.main.extract_structured_data",
        side_effect=simulate_rate_limit,
    ):
        try:
            extract_structured(payload)

        except HTTPException as exc:
            assert exc.status_code == 429, (
                f"Expected HTTP 429, got {exc.status_code}"
            )
            print("PASS: Gemini rate limit returns HTTP 429")

        else:
            raise AssertionError(
                "Expected an HTTPException, but none was raised"
            )


def simulate_service_unavailable(**kwargs):
    raise errors.ServerError(
        code=503,
        response_json={
            "error": {
                "code": 503,
                "message": "Service temporarily unavailable",
                "status": "UNAVAILABLE",
            }
        },
    )


def test_gemini_service_unavailable():
    payload = StructuredExtractionRequest(
        text="Invoice number INV-001",
        document_type="invoice",
    )

    with patch(
        "app.main.extract_structured_data",
        side_effect=simulate_service_unavailable,
    ):
        try:
            extract_structured(payload)

        except HTTPException as exc:
            assert exc.status_code == 503, (
                f"Expected HTTP 503, got {exc.status_code}"
            )
            print("PASS: Gemini service unavailable returns HTTP 503")

        else:
            raise AssertionError(
                "Expected an HTTPException, but none was raised"
            )


def simulate_unexpected_error(**kwargs):
    raise ValueError("Simulated unexpected extraction error")


def test_unexpected_extraction_error():
    payload = StructuredExtractionRequest(
        text="Invoice number INV-001",
        document_type="invoice",
    )

    with patch(
        "app.main.extract_structured_data",
        side_effect=simulate_unexpected_error,
    ):
        try:
            extract_structured(payload)

        except HTTPException as exc:
            assert exc.status_code == 500, (
                f"Expected HTTP 500, got {exc.status_code}"
            )

            assert exc.detail == (
                "An unexpected extraction error occurred."
            )

            print("PASS: Unexpected extraction error returns HTTP 500")

        else:
            raise AssertionError(
                "Expected an HTTPException, but none was raised"
            )


if __name__ == "__main__":
    test_gemini_rate_limit()
    test_gemini_service_unavailable()
    test_unexpected_extraction_error()
