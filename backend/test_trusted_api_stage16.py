
import asyncio
import io
import tempfile
from pathlib import Path
from unittest.mock import patch

import pymupdf
from fastapi import UploadFile

from app import cache, main


def create_test_pdf():
    """Create a small PDF containing fictional invoice text."""
    document = pymupdf.open()
    page = document.new_page()
    page.insert_text(
        (72, 72),
        "Invoice TEST-TRUSTED-001\n"
        "Exporter: Example Supplier\n"
        "Total: USD 500",
    )
    pdf_bytes = document.tobytes()
    document.close()
    return pdf_bytes


def fail_if_gemini_called(*args, **kwargs):
    raise AssertionError("Gemini must NOT be called for a cache HIT")


async def run_test():
    pdf_bytes = create_test_pdf()

    trusted_data = {
        "invoice_number": "TEST-TRUSTED-001",
        "exporter": "Example Supplier",
        "consignee": "Example Importer",
        "currency": "USD",
        "items": [],
        "total_amount": 500,
    }

    with tempfile.TemporaryDirectory() as temporary_directory:
        with patch.object(cache, "CACHE_DIR", Path(temporary_directory)):
            cache_key = cache.generate_cache_key(
                pdf_bytes,
                "invoice",
            )

            cache.save_cached_result(
                cache_key,
                trusted_data,
                source="gemini_live",
            )

            upload = UploadFile(
                filename="trusted_test_invoice.pdf",
                file=io.BytesIO(pdf_bytes),
            )

            with patch.object(
                main,
                "extract_structured_data",
                side_effect=fail_if_gemini_called,
            ):
                response = await main.upload_and_extract(
                    file=upload,
                    document_type="invoice",
                )

            assert response["from_cache"] is True
            assert response["extraction_source"] == "gemini_live"
            assert response["extracted_data"] == trusted_data

            print("Trusted-cache API test: PASS")
            print("Gemini API calls: 0")
            print("Extraction source: gemini_live")


if __name__ == "__main__":
    asyncio.run(run_test())
