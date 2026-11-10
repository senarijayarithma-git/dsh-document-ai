
import argparse
import sys
from pathlib import Path

from openpyxl import load_workbook
from sqlalchemy import select

BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE_DIR))

from app.database import SessionLocal
from app.nmra_models import NMRARegistration, NMRAProductMapping
from preview_nmra_import import classify_nmra, clean


EXCEL_FILE = BASE_DIR / "data" / "Copy of NMRA List (2).xlsx"
SHEET_NAME = "NMRA LIST (2)"


def read_candidate_mappings():
    workbook = load_workbook(
        EXCEL_FILE,
        read_only=True,
        data_only=True,
    )

    mappings = {}

    try:
        sheet = workbook[SHEET_NAME]

        for row_number, row in enumerate(
            sheet.iter_rows(min_row=2, values_only=True),
            start=2,
        ):
            item_code = clean(row[0])
            description = clean(row[1])
            nmra_value = clean(row[14])

            if not item_code:
                continue

            if classify_nmra(nmra_value) != "CANDIDATE_REGISTRATION":
                continue

            key = (item_code.upper(), nmra_value.upper())

            if key not in mappings:
                mappings[key] = {
                    "item_code": item_code,
                    "description": description or None,
                    "d_number": nmra_value,
                    "source_file": EXCEL_FILE.name,
                    "source_row": row_number,
                }

    finally:
        workbook.close()

    return mappings


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--apply",
        action="store_true",
        help="Write approved candidate records to PostgreSQL",
    )
    args = parser.parse_args()

    mappings = read_candidate_mappings()

    registration_numbers = sorted({
        record["d_number"].upper()
        for record in mappings.values()
    })

    print("\nNMRA DATABASE IMPORT")
    print("=" * 40)
    print("Unique candidate registrations:", len(registration_numbers))
    print("Unique candidate mappings:", len(mappings))

    with SessionLocal() as db:
        existing_registrations = {
            number.upper()
            for number in db.scalars(
                select(NMRARegistration.d_number)
            ).all()
        }

        existing_mappings = {
            (code.upper(), number.upper())
            for code, number in db.execute(
                select(
                    NMRAProductMapping.item_code,
                    NMRAProductMapping.d_number,
                )
            ).all()
        }

        new_registrations = [
            number
            for number in registration_numbers
            if number not in existing_registrations
        ]

        new_mappings = [
            record
            for key, record in mappings.items()
            if key not in existing_mappings
        ]

        print("New registrations:", len(new_registrations))
        print("New mappings:", len(new_mappings))

        if not args.apply:
            print("\nDRY RUN: No database changes made.")
            print("Run with --apply only after reviewing results.")
            return

        try:
            for number in new_registrations:
                db.add(
                    NMRARegistration(d_number=number)
                )

            db.flush()

            for record in new_mappings:
                db.add(
                    NMRAProductMapping(
                        client_id=None,
                        item_code=record["item_code"],
                        product_description=record["description"],
                        d_number=record["d_number"].upper(),
                        source_file=record["source_file"],
                        source_row=record["source_row"],
                    )
                )

            db.commit()
            print("\nIMPORT COMPLETE.")

        except Exception:
            db.rollback()
            raise


if __name__ == "__main__":
    main()
