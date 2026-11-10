
import argparse
import re
from pathlib import Path

import pymupdf
import pytesseract
from PIL import Image, ImageEnhance, ImageOps
from sqlalchemy import func, select

from app.database import SessionLocal
from app.nmra_models import NMRAAttachment, NMRAAttachmentItem


BACKEND_DIR = Path(__file__).resolve().parents[1]
STORAGE_DIR = BACKEND_DIR / "storage"

pytesseract.pytesseract.tesseract_cmd = (
    r"C:\Program Files\Tesseract-OCR\tesseract.exe"
)

CODE_PATTERN = re.compile(
    r"(?:XSYS\d{4}|BLT\d{5})",
    re.IGNORECASE,
)

def extract_page_items(page, page_number):
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

        # The first column normally contains the
        # numbered table row, e.g. "70 XSYS0027".
        row_number = None
        row_match = re.search(
            rf"(?:^|[\s|[\]])"
            rf"(\d{{1,3}})"
            rf"\s*[.,:|\-—]*\s*"
            rf"{re.escape(code)}\b",
            evidence,
            re.IGNORECASE,
        )

        if row_match:
            row_number = int(row_match.group(1))

        # Product description is deliberately left empty
        # until table-column extraction is reliable.
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


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--attachment-id",
        type=int,
        default=1,
    )
    parser.add_argument(
        "--apply",
        action="store_true",
    )
    parser.add_argument(
        "--allow-unreviewed",
        action="store_true",
        help="Save incomplete OCR candidates for manual review.",
    )

    args = parser.parse_args()

    with SessionLocal() as db:
        attachment = db.get(
            NMRAAttachment,
            args.attachment_id,
        )

        if attachment is None:
            raise SystemExit(
                f"Attachment {args.attachment_id} not found."
            )

        if attachment.review_status != "PENDING":
            raise SystemExit(
                "Indexing stopped: attachment is not PENDING."
            )

        existing_count = db.scalar(
            select(func.count())
            .select_from(NMRAAttachmentItem)
            .where(
                NMRAAttachmentItem.attachment_id
                == attachment.id
            )
        )

        if existing_count:
            raise SystemExit(
                f"Indexing stopped: {existing_count} "
                "items already exist for this attachment."
            )

        # Resolve the stored relative path beneath
        # the backend storage directory.
        pdf_path = (
            STORAGE_DIR / attachment.storage_key
        ).resolve()

        if not pdf_path.is_relative_to(STORAGE_DIR.resolve()):
            raise SystemExit(
                "Unsafe attachment storage path."
            )

        if not pdf_path.is_file():
            raise SystemExit(
                f"PDF not found: {pdf_path}"
            )

        items = []

        with pymupdf.open(pdf_path) as document:
            for page_number, page in enumerate(
                document,
                start=1,
            ):
                page_items = extract_page_items(
                    page,
                    page_number,
                )

                print(
                    f"Page {page_number}: "
                    f"{len(page_items)} candidate codes"
                )

                items.extend(page_items)

        # Avoid duplicate code/page pairs in the same run.
        unique_items = {}
        for item in items:
            key = (
                item["item_code"],
                item["page_number"],
            )
            unique_items.setdefault(key, item)

        items = list(unique_items.values())


        print("\nROW SEQUENCE VALIDATION")
        print("=" * 55)

        sequence_issues = []

        for index, item in enumerate(items):
            current_row = item["row_number"]

            if current_row is None:
                continue

            previous_row = None

            for previous in reversed(items[:index]):
                if previous["row_number"] is not None:
                    previous_row = previous["row_number"]
                    break

            if previous_row is None:
                continue

            difference = current_row - previous_row

            if difference <= 0 or difference > 2:
                sequence_issues.append(
                    {
                        "item_code": item["item_code"],
                        "page_number": item["page_number"],
                        "previous_row": previous_row,
                        "detected_row": current_row,
                        "difference": difference,
                    }
                )

        print(
            "Suspicious row transitions:",
            len(sequence_issues)
        )

        for issue in sequence_issues:
            print(
                f"Page {issue['page_number']} | "
                f"{issue['item_code']} | "
                f"Previous: {issue['previous_row']} | "
                f"Detected: {issue['detected_row']} | "
                f"Difference: {issue['difference']}"
            )

        missing_rows = [
            item for item in items
            if item["row_number"] is None
        ]

        suspicious_rows = [
            item for item in items
            if item["row_number"] is not None
            and (
                item["row_number"] < 1
                or item["row_number"] > 117
            )
        ]

        print("\nOCR QUALITY CHECK")
        print("=" * 55)
        print("Total candidates:", len(items))
        print("Missing row numbers:", len(missing_rows))
        print("Out-of-range row numbers:", len(suspicious_rows))

        print("\nRECORDS WITH MISSING ROW NUMBERS:")
        for item in missing_rows:
            print(
                f"Page {item['page_number']}: "
                f"{item['item_code']} | "
                f"{item['evidence_text'][:100]}"
            )

        print("\nOUT-OF-RANGE ROW NUMBERS:")
        for item in suspicious_rows:
            print(
                f"Page {item['page_number']}: "
                f"{item['item_code']} | "
                f"row={item['row_number']}"
            )

        print("\nNMRA ATTACHMENT INDEX PREVIEW")
        print("=" * 55)
        print("Attachment ID:", attachment.id)
        print("Filename:", attachment.filename)
        print("Candidate records:", len(items))

        for item in items:
            print(
                f"{item['item_code']:<14} "
                f"page={item['page_number']:<2} "
                f"row={str(item['row_number']):<5} "
                f"{item['evidence_text'][:85]}"
            )

        print("\nATTACHMENT COMPLETENESS CHECK")
        print("=" * 55)

        detected_count = len(items)

        valid_row_numbers = [
            item["row_number"]
            for item in items
            if item["row_number"] is not None
            and 1 <= item["row_number"] <= 117
        ]

        highest_row = (
            max(valid_row_numbers)
            if valid_row_numbers
            else None
        )

        print("Detected OCR candidates:", detected_count)
        print("Highest plausible row:", highest_row)

        if highest_row is not None:
            print(
                "Candidate count versus highest row:",
                detected_count,
                "/",
                highest_row,
            )
            print(
                "Manual completeness review required."
            )

        if not args.apply:
            print("\nDRY RUN: No database changes made.")
            print("Use --apply only after reviewing results.")
            return

        if missing_rows or suspicious_rows or sequence_issues:
            print("\nOCR REVIEW REQUIRED")
            print("=" * 55)
            print("Missing row numbers:", len(missing_rows))
            print("Out-of-range rows:", len(suspicious_rows))
            print("Suspicious transitions:", len(sequence_issues))

            if not args.allow_unreviewed:
                print(
                    "INDEXING BLOCKED: OCR issues require review."
                )
                print(
                    "Use --allow-unreviewed only to save "
                    "candidates for employee review."
                )
                return

            print(
                "Review-only indexing permitted. "
                "All candidates remain UNREVIEWED."
            )

        for item in items:
            item["review_status"] = "UNREVIEWED"

        attachment.review_status = "PENDING"
        attachment.approved_at = None
        attachment.approved_by = None

        if any(
            item["review_status"] != "UNREVIEWED"
            for item in items
        ):
            raise SystemExit(
                "Indexing stopped: OCR candidates "
                "must remain UNREVIEWED."
            )

        for item in items:
            db.add(
                NMRAAttachmentItem(
                    attachment_id=attachment.id,
                    **item,
                )
            )

        db.commit()

        print(
            f"\nSaved {len(items)} UNREVIEWED "
            "OCR candidate records."
        )
        print(
            "Attachment remains PENDING. "
            "No regulatory approval was granted."
        )


if __name__ == "__main__":
    main()
