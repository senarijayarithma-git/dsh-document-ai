
import argparse
import sys
from pathlib import Path

from sqlalchemy import select

BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE_DIR))

from app.database import SessionLocal
from app.nmra_models import NMRARegistration, NMRAAttachment


D_NUMBER = "D/4568"

CERTIFICATE = (
    BASE_DIR
    / "storage"
    / "nmra"
    / "certificates"
    / "NMRA D 4568_11zon.pdf"
)

ATTACHMENT = (
    BASE_DIR
    / "storage"
    / "nmra"
    / "attachments"
    / "D-4568 - NEW ATTACHMENT - 2026.pdf"
)

ATTACHMENT_STORAGE_KEY = (
    "nmra/attachments/D-4568 - NEW ATTACHMENT - 2026.pdf"
)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--apply", action="store_true")
    args = parser.parse_args()

    if not CERTIFICATE.is_file():
        raise FileNotFoundError(CERTIFICATE)

    if not ATTACHMENT.is_file():
        raise FileNotFoundError(ATTACHMENT)

    with SessionLocal() as db:
        registration = db.scalar(
            select(NMRARegistration).where(
                NMRARegistration.d_number == D_NUMBER
            )
        )

        if registration is None:
            raise RuntimeError(
                f"Registration {D_NUMBER} not found."
            )

        existing_attachment = db.scalar(
            select(NMRAAttachment).where(
                NMRAAttachment.storage_key == ATTACHMENT_STORAGE_KEY
            )
        )

        print("\nNMRA DOCUMENT REGISTRATION")
        print("=" * 40)
        print("D Number:", registration.d_number)
        print("Registration ID:", registration.id)
        print("Certificate:", CERTIFICATE.name)
        print("Attachment:", ATTACHMENT.name)
        print("Attachment already registered:", existing_attachment is not None)

        if not args.apply:
            print("\nDRY RUN: No database changes made.")
            return

        if (
            registration.certificate_filename
            and registration.certificate_filename != CERTIFICATE.name
        ):
            raise RuntimeError(
                "A different certificate is already registered. "
                "Manual review required."
            )

        try:
            registration.certificate_filename = CERTIFICATE.name

            if existing_attachment is None:
                attachment = NMRAAttachment(
                    registration_id=registration.id,
                    filename=ATTACHMENT.name,
                    storage_key=ATTACHMENT_STORAGE_KEY,
                    version=1,
                    review_status="PENDING",
                )
                db.add(attachment)

            db.commit()
            print("\nDOCUMENT REGISTRATION COMPLETE.")
            print("Attachment approval status: PENDING")

        except Exception:
            db.rollback()
            raise


if __name__ == "__main__":
    main()
