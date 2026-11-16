
from unittest.mock import patch

import pymupdf
import pytest

from app.nmra_pdf_service import (
    MAX_PDF_BYTES,
    MAX_PDF_PAGES,
    NMRAInvalidPDFError,
    NMRAPDFLimitError,
    extract_nmra_pdf_pages,
)


def make_pdf(texts):
    pdf = pymupdf.open()

    for text in texts:
        page = pdf.new_page()
        if text:
            page.insert_text((72, 72), text)

    data = pdf.tobytes()
    pdf.close()
    return data


def test_extracts_embedded_text():
    data = make_pdf(["NMRA D-1499", "Product ABC"])

    with patch(
        "app.nmra_pdf_service.configure_tesseract"
    ) as configure:
        pages = extract_nmra_pdf_pages(data)

    assert len(pages) == 2
    assert pages[0].page_number == 1
    assert "D-1499" in pages[0].text
    assert pages[0].method == "pdf_text"
    assert pages[1].page_number == 2
    assert "Product ABC" in pages[1].text
    configure.assert_not_called()


def test_uses_ocr_for_scanned_page():
    data = make_pdf([""])

    with (
        patch(
            "app.nmra_pdf_service.configure_tesseract"
        ) as configure,
        patch(
            "app.nmra_pdf_service.pytesseract.image_to_string",
            return_value="Scanned NMRA certificate",
        ) as ocr,
    ):
        pages = extract_nmra_pdf_pages(data)

    assert len(pages) == 1
    assert pages[0].method == "ocr"
    assert pages[0].text == "Scanned NMRA certificate"
    configure.assert_called_once()
    ocr.assert_called_once()


def test_rejects_non_pdf():
    with pytest.raises(NMRAInvalidPDFError):
        extract_nmra_pdf_pages(b"not a PDF")


def test_rejects_corrupted_pdf():
    with pytest.raises(NMRAInvalidPDFError):
        extract_nmra_pdf_pages(b"%PDF-this-is-corrupted")


def test_rejects_oversized_pdf():
    data = b"%PDF-" + b"x" * MAX_PDF_BYTES

    with pytest.raises(NMRAPDFLimitError):
        extract_nmra_pdf_pages(data)


def test_rejects_too_many_pages():
    data = make_pdf([""] * (MAX_PDF_PAGES + 1))

    with pytest.raises(NMRAPDFLimitError):
        extract_nmra_pdf_pages(data)
