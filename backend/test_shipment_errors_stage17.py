
import asyncio
import io
from unittest.mock import patch

import pymupdf
from fastapi import HTTPException, UploadFile
from google.genai import errors

from app.main import upload_and_verify_shipment


def create_test_pdf():
    """Create a valid PDF in memory without using Gemini."""
    pdf = pymupdf.open()
    page = pdf.new_page()
    page.insert_text((72, 72), "Invoice number INV-001")
    data = pdf.tobytes()
    pdf.close()
    return data


def simulate_rate_limit(*args, **kwargs):
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


async def test_shipment_rate_limit():
    pdf_bytes = create_test_pdf()

    def make_upload(filename):
        return UploadFile(
            filename=filename,
            file=io.BytesIO(pdf_bytes),
            headers={"content-type": "application/pdf"},
        )

    invoice = make_upload("stage17_invoice.pdf")
    packing = make_upload("stage17_packing.pdf")
    awb = make_upload("stage17_awb.pdf")

    with (
        patch("app.main.get_cached_result", return_value=None),
        patch(
            "app.main.extract_structured_data",
            side_effect=simulate_rate_limit,
        ),
    ):
        try:
            await upload_and_verify_shipment(
                invoice_file=invoice,
                packing_list_file=packing,
                air_waybill_file=awb,
            )

        except HTTPException as exc:
            assert exc.status_code == 429, (
                f"Expected HTTP 429, got {exc.status_code}"
            )
            assert "invoice" in exc.detail
            print("PASS: Shipment Gemini rate limit returns HTTP 429")

        else:
            raise AssertionError(
                "Expected HTTPException, but none was raised"
            )

def simulate_service_unavailable(*args, **kwargs):
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


async def test_shipment_service_unavailable():
    pdf_bytes = create_test_pdf()

    def make_upload(filename):
        return UploadFile(
            filename=filename,
            file=io.BytesIO(pdf_bytes),
            headers={"content-type": "application/pdf"},
        )

    invoice = make_upload("stage17_invoice.pdf")
    packing = make_upload("stage17_packing.pdf")
    awb = make_upload("stage17_awb.pdf")

    with (
        patch("app.main.get_cached_result", return_value=None),
        patch(
            "app.main.extract_structured_data",
            side_effect=simulate_service_unavailable,
        ),
    ):
        try:
            await upload_and_verify_shipment(
                invoice_file=invoice,
                packing_list_file=packing,
                air_waybill_file=awb,
            )

        except HTTPException as exc:
            assert exc.status_code == 503, (
                f"Expected HTTP 503, got {exc.status_code}"
            )
            assert "invoice" in exc.detail

            print("PASS: Shipment Gemini unavailable returns HTTP 503")

        else:
            raise AssertionError(
                "Expected HTTPException, but none was raised"
            )

def simulate_unexpected_error(*args, **kwargs):
    raise ValueError("Simulated unexpected extraction error")


async def test_shipment_unexpected_error():
    pdf_bytes = create_test_pdf()

    def make_upload(filename):
        return UploadFile(
            filename=filename,
            file=io.BytesIO(pdf_bytes),
            headers={"content-type": "application/pdf"},
        )

    invoice = make_upload("stage17_invoice.pdf")
    packing = make_upload("stage17_packing.pdf")
    awb = make_upload("stage17_awb.pdf")

    with (
        patch("app.main.get_cached_result", return_value=None),
        patch(
            "app.main.extract_structured_data",
            side_effect=simulate_unexpected_error,
        ),
    ):
        try:
            await upload_and_verify_shipment(
                invoice_file=invoice,
                packing_list_file=packing,
                air_waybill_file=awb,
            )

        except HTTPException as exc:
            assert exc.status_code == 500, (
                f"Expected HTTP 500, got {exc.status_code}"
            )
            assert "invoice" in exc.detail

            print("PASS: Shipment unexpected error returns HTTP 500")

        else:
            raise AssertionError(
                "Expected HTTPException, but none was raised"
            )

if __name__ == "__main__":
    asyncio.run(test_shipment_rate_limit())
    asyncio.run(test_shipment_service_unavailable())
    asyncio.run(test_shipment_unexpected_error())