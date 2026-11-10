
from collections import Counter
from pathlib import Path
import re

from openpyxl import load_workbook


BASE_DIR = Path(__file__).resolve().parent.parent
EXCEL_FILE = BASE_DIR / "data" / "Copy of NMRA List (2).xlsx"

STATUS_VALUES = {
    "discontinued",
    "discontiuned",
    "no registration",
    "registration not required",
}

REVIEW_VALUES = {
    "lp",
    "riqas",
}

# A candidate format is not proof of regulatory validity.
REGISTRATION_PATTERN = re.compile(
    r"^[A-Z][A-Z0-9]*/[A-Z0-9][A-Z0-9/\-]*$",
    re.IGNORECASE,
)


def clean(value):
    if value is None:
        return ""
    return str(value).replace("\xa0", " ").strip()


def classify_nmra(value):
    normalized = " ".join(value.lower().split())

    if not normalized or value.startswith("#"):
        return "MISSING"

    if normalized in STATUS_VALUES:
        return "STATUS"

    if normalized in REVIEW_VALUES:
        return "NEEDS_REVIEW"

    if REGISTRATION_PATTERN.fullmatch(value):
        return "CANDIDATE_REGISTRATION"

    return "NEEDS_REVIEW"


def main():
    if not EXCEL_FILE.exists():
        raise FileNotFoundError(EXCEL_FILE)

    workbook = load_workbook(
        EXCEL_FILE,
        read_only=True,
        data_only=True,
    )

    try:
        sheet = workbook["NMRA LIST (2)"]

        counts = Counter()
        unique_mappings = {}
        review_examples = []

        for row_number, row in enumerate(
            sheet.iter_rows(min_row=2, values_only=True),
            start=2,
        ):
            item_code = clean(row[0])
            description = clean(row[1])
            nmra_value = clean(row[14])

            if not item_code:
                counts["MISSING_ITEM_CODE"] += 1
                continue

            classification = classify_nmra(nmra_value)
            counts[classification] += 1

            if classification == "CANDIDATE_REGISTRATION":
                key = (item_code.upper(), nmra_value.upper())

                if key not in unique_mappings:
                    unique_mappings[key] = {
                        "item_code": item_code,
                        "description": description,
                        "d_number": nmra_value,
                        "source_row": row_number,
                    }

            elif len(review_examples) < 10:
                review_examples.append(
                    (row_number, item_code, nmra_value, classification)
                )

        print("\nNMRA EXCEL IMPORT PREVIEW")
        print("=" * 40)

        for category, count in sorted(counts.items()):
            print(f"{category}: {count}")

        print(
            "\nUnique candidate registration mappings:",
            len(unique_mappings),
        )

        print("\nExamples requiring review:")
        for example in review_examples:
            print(example)

        print("\nPREVIEW ONLY: No database changes made.")

    finally:
        workbook.close()


if __name__ == "__main__":
    main()
