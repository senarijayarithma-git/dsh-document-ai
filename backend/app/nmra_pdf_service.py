import io
from dataclasses import dataclass

import pymupdf
import pytesseract
from PIL import Image

from app.ocr_config import configure_tesseract


MAX_PDF_BYTES = 10 * 1024 * 1024
MAX_PDF_PAGES = 30


class NMRAInvalidPDFError(ValueError):
    pass


class NMRAPDFLimitError(ValueError):
    pass


@dataclass(frozen=True)
class ExtractedPage:
    page_number: int
    text: str
    method: str


def extract_nmra_pdf_pages(data: bytes) -> list[ExtractedPage]:
    """Extract searchable text from a PDF, using OCR when needed."""

    if len(data) > MAX_PDF_BYTES:
        raise NMRAPDFLimitError("PDF exceeds 10 MiB limit")

    if not data.startswith(b"%PDF-"):
        raise NMRAInvalidPDFError("Expected a PDF file")

    pages: list[ExtractedPage] = []

    try:
        with pymupdf.open(stream=data, filetype="pdf") as pdf:
            if pdf.needs_pass:
                raise NMRAInvalidPDFError(
                    "Password-protected PDFs are not supported"
                )

            if pdf.page_count == 0:
                raise NMRAInvalidPDFError("PDF contains no pages")

            if pdf.page_count > MAX_PDF_PAGES:
                raise NMRAPDFLimitError(
                    "PDF exceeds 30 pages"
                )

            for page_number, page in enumerate(pdf, start=1):
                text = page.get_text("text").strip()
                method = "pdf_text"

                if not text:
                    configure_tesseract()

                    pix = page.get_pixmap(
                        matrix=pymupdf.Matrix(2, 2),
                        alpha=False,
                    )

                    image = Image.open(
                        io.BytesIO(pix.tobytes("png"))
                    )

                    text = pytesseract.image_to_string(
                        image,
                        lang="eng",
                    ).strip()

                    method = "ocr"

                pages.append(
                    ExtractedPage(
                        page_number=page_number,
                        text=text,
                        method=method,
                    )
                )

    except (NMRAInvalidPDFError, NMRAPDFLimitError):
        raise
    except (
        pymupdf.FileDataError,
        pymupdf.EmptyFileError,
    ) as exc:
        raise NMRAInvalidPDFError(
            "Invalid or corrupted PDF"
        ) from exc

    return pages
