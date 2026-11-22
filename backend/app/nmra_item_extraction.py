
import re
from pathlib import Path

import pymupdf
import pytesseract
from PIL import Image, ImageEnhance, ImageOps


CODE_PATTERN = re.compile(
    r"(?:XSYS\d{4}|BLT\d{5})",
    re.IGNORECASE,
)

TESSERACT_PATH = Path(
    r"C:\Program Files\Tesseract-OCR\tesseract.exe"
)

if TESSERACT_PATH.is_file():
    pytesseract.pytesseract.tesseract_cmd = str(TESSERACT_PATH)


def extract_page_items(page, page_number: int) -> list[dict]:
    pixmap = page.get_pixmap(
        matrix=pymupdf.Matrix(3, 3),
        alpha=False,
    )

    image = Image.frombytes(
        "RGB",
        (pixmap.width, pixmap.height),
        pixmap.samples,
    )

    image = ImageOps.grayscale(image)
    image = ImageEnhance.Contrast(image).enhance(1.5)

    data = pytesseract.image_to_data(
        image,
        lang="eng",
        config="--oem 3 --psm 11",
        output_type=pytesseract.Output.DICT,
    )

    results = []

    for i, raw_text in enumerate(data["text"]):
        code = raw_text.strip().upper()

        if not CODE_PATTERN.fullmatch(code):
            continue

        code_y = data["top"][i]
        code_height = data["height"][i]

        nearby = []

        for j, word in enumerate(data["text"]):
            word = word.strip()

            if not word:
                continue

            word_y = data["top"][j]
            word_height = data["height"][j]

            if (
                word_y < code_y + code_height + 12
                and word_y + word_height > code_y - 12
            ):
                nearby.append((data["left"][j], word))

        nearby.sort(key=lambda entry: entry[0])

        evidence = " ".join(
            word for _, word in nearby
        )[:1000]

        row_number = None

        row_match = re.search(
            rf"(?:^|[\s|\[\]])"
            rf"(\d{{1,3}})"
            rf"\s*[.,:|\-—]*\s*"
            rf"{re.escape(code)}\b",
            evidence,
            re.IGNORECASE,
        )

        if row_match:
            row_number = int(row_match.group(1))

        results.append(
            {
                "item_code": code,
                "product_description": None,
                "page_number": page_number,
                "row_number": row_number,
                "evidence_text": evidence,
                "extraction_method": "OCR",
                "review_status": "UNREVIEWED",
            }
        )

    return results


def extract_attachment_items(pdf_path: Path) -> list[dict]:
    items = []

    with pymupdf.open(pdf_path) as document:
        for page_number, page in enumerate(document, start=1):
            items.extend(
                extract_page_items(page, page_number)
            )

    unique_items = {}

    for item in items:
        key = (
            item["item_code"],
            item["page_number"],
        )
        unique_items.setdefault(key, item)

    return list(unique_items.values())
