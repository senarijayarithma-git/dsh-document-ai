
import pymupdf
from fastapi.testclient import TestClient
from app.main import app


client = TestClient(app)


def test_extract_text_valid_pdf():
    # Create a small PDF in memory
    pdf = pymupdf.open()
    page = pdf.new_page()

    page.insert_text(
        (72, 72),
        "DSH Global Logistics Test Invoice"
    )

    pdf_bytes = pdf.tobytes()
    pdf.close()

    # Upload the PDF to FastAPI
    response = client.post(
        "/documents/extract-text",
        files={
            "file": (
                "test_invoice.pdf",
                pdf_bytes,
                "application/pdf"
            )
        }
    )

    # Check the HTTP response
    assert response.status_code == 200

    data = response.json()

    # Check the returned filename
    assert data["filename"] == "test_invoice.pdf"

    # Check that one page was processed
    assert len(data["pages"]) == 1

    # Check that the expected text was extracted
    assert (
        "DSH Global Logistics Test Invoice"
        in data["pages"][0]["text"]
    )

    # Check that normal PDF text extraction was used
    assert data["pages"][0]["method"] == "pdf_text"

    # OCR should not be necessary
    assert data["needs_ocr"] is False


def test_extract_text_rejects_non_pdf():
    response = client.post(
        "/documents/extract-text",
        files={
            "file": (
                "not_a_pdf.txt",
                b"This is a text file, not a PDF.",
                "text/plain"
            )
        }
    )

    assert response.status_code == 400

    assert response.json()["detail"] == "Expected a PDF"

def test_extract_text_rejects_oversized_pdf():
    # Create fake PDF bytes larger than 10 MB.
    # A complete PDF is unnecessary because the size
    # check happens before PDF processing.
    oversized_pdf = (
        b"%PDF-1.4\n"
        + b"A" * (10 * 1024 * 1024)
    )

    response = client.post(
        "/documents/extract-text",
        files={
            "file": (
                "large_document.pdf",
                oversized_pdf,
                "application/pdf"
            )
        }
    )

    assert response.status_code == 413

    assert (
        response.json()["detail"]
        == "File exceeds 10 MB limit"
    )

def test_extract_text_rejects_too_many_pages():
    # Create a PDF containing 31 blank pages
    pdf = pymupdf.open()

    for _ in range(31):
        pdf.new_page()

    pdf_bytes = pdf.tobytes()
    pdf.close()

    # Upload the PDF to the backend
    response = client.post(
        "/documents/extract-text",
        files={
            "file": (
                "31_page_document.pdf",
                pdf_bytes,
                "application/pdf"
            )
        }
    )

    # The backend should reject PDFs over 30 pages
    assert response.status_code == 413

    assert (
        response.json()["detail"]
        == "More than 30 pages"
    )

def test_extract_text_missing_file():
    # Send a request without attaching a file
    response = client.post(
        "/documents/extract-text"
    )

    # FastAPI should reject the missing required file
    assert response.status_code == 422

    errors = response.json()["detail"]

    # Confirm that the missing field is "file"
    assert any(
        error["loc"] == ["body", "file"]
        for error in errors
    )
