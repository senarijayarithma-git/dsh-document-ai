from datetime import datetime, timezone

from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session
from sqlalchemy.pool import StaticPool

from app.database import Base, get_db
from app.db_models import Document
from app.main import app


def test_document_retrieval():
    test_engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )

    Base.metadata.create_all(bind=test_engine)

    with Session(test_engine) as db:
        db.add(
            Document(
                filename="test_invoice.pdf",
                document_type="invoice",
                status="processed",
                uploaded_at=datetime.now(timezone.utc),
            )
        )
        db.commit()

    def override_get_db():
        with Session(test_engine) as db:
            yield db

    app.dependency_overrides[get_db] = override_get_db

    try:
        with TestClient(app) as client:
            # Test 1: Retrieve all documents
            response = client.get("/documents")

            assert response.status_code == 200
            assert len(response.json()) == 1
            assert response.json()[0]["filename"] == "test_invoice.pdf"

            # Test 2: Retrieve document ID 1
            response = client.get("/documents/1")

            assert response.status_code == 200
            assert response.json()["status"] == "processed"

            # Test 3: Retrieve a missing document
            response = client.get("/documents/999")

            assert response.status_code == 404
            assert response.json()["detail"] == "Document not found"

    finally:
        app.dependency_overrides.pop(get_db, None)
        test_engine.dispose()