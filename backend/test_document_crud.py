
from sqlalchemy import select

from app.database import SessionLocal
from app.db_models import Document


def main():
    with SessionLocal() as db:

        # CREATE: Save a document record
        new_document = Document(
            filename="sample_invoice.pdf",
            document_type="invoice",
            status="uploaded"
        )

        db.add(new_document)
        db.commit()
        db.refresh(new_document)

        print("DOCUMENT SAVED SUCCESSFULLY!")
        print("Document ID:", new_document.id)

        # READ: Retrieve the same document
        statement = select(Document).where(
            Document.id == new_document.id
        )

        saved_document = db.scalar(statement)

        print("\nDOCUMENT RETRIEVED!")
        print("ID:", saved_document.id)
        print("Filename:", saved_document.filename)
        print("Type:", saved_document.document_type)
        print("Status:", saved_document.status)
        print("Uploaded at:", saved_document.uploaded_at)


if __name__ == "__main__":
    main()
