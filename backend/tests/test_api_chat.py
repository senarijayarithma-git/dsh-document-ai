from fastapi.testclient import TestClient
from app.main import app
from unittest.mock import MagicMock, patch
from app.main import get_db

client = TestClient(app)


def test_chat_rejects_invalid_document_id():
    response = client.post(
        "/chat/ask",
        json={
            "document_id": 0,
            "question": "Who is the exporter?"
        }
    )

    assert response.status_code == 422

def test_chat_document_not_found():
    fake_db = MagicMock()
    fake_db.get.return_value = None

    def override_get_db():
        yield fake_db

    app.dependency_overrides[get_db] = override_get_db

    try:
        response = client.post(
            "/chat/ask",
            json={
                "document_id": 999999,
                "question": "Who is the exporter?"
            }
        )

        assert response.status_code == 404
        assert response.json() == {
            "detail": "Document not found"
        }

    finally:
        app.dependency_overrides.pop(get_db, None)

def test_chat_document_without_extracted_data():
    fake_document = MagicMock()
    fake_document.extracted_data = None

    fake_db = MagicMock()
    fake_db.get.return_value = fake_document

    def override_get_db():
        yield fake_db

    app.dependency_overrides[get_db] = override_get_db

    try:
        response = client.post(
            "/chat/ask",
            json={
                "document_id": 3,
                "question": "Who is the exporter?"
            }
        )

        assert response.status_code == 400
        assert response.json() == {
            "detail": "This document has no extracted data"
        }

    finally:
        app.dependency_overrides.pop(get_db, None)

def test_chat_successful_response():
    fake_document = MagicMock()
    fake_document.id = 3
    fake_document.extracted_data = {
        "exporter": "SIEMENS HEALTHCARE PVT. LTD."
    }

    fake_db = MagicMock()
    fake_db.get.return_value = fake_document

    def override_get_db():
        yield fake_db

    app.dependency_overrides[get_db] = override_get_db

    try:
        with patch(
            "app.main.answer_document_question",
            return_value="The exporter is SIEMENS HEALTHCARE PVT. LTD."
        ) as mock_chat:

            response = client.post(
                "/chat/ask",
                json={
                    "document_id": 3,
                    "question": "Who is the exporter?"
                }
            )

            assert response.status_code == 200

            assert response.json() == {
                "document_id": 3,
                "question": "Who is the exporter?",
                "answer": "The exporter is SIEMENS HEALTHCARE PVT. LTD."
            }

            mock_chat.assert_called_once_with(
                extracted_data=fake_document.extracted_data,
                question="Who is the exporter?"
            )

    finally:
        app.dependency_overrides.pop(get_db, None)

def test_chat_gemini_service_failure():
    fake_document = MagicMock()
    fake_document.id = 3
    fake_document.extracted_data = {
        "exporter": "SIEMENS HEALTHCARE PVT. LTD."
    }

    fake_db = MagicMock()
    fake_db.get.return_value = fake_document

    def override_get_db():
        yield fake_db

    app.dependency_overrides[get_db] = override_get_db

    try:
        with patch(
            "app.main.answer_document_question",
            side_effect=RuntimeError("Gemini API unavailable")
        ):
            response = client.post(
                "/chat/ask",
                json={
                    "document_id": 3,
                    "question": "Who is the exporter?"
                }
            )

        assert response.status_code == 503

        assert response.json() == {
            "detail": (
                "AI chatbot service is temporarily unavailable. "
                "Please try again later."
            )
        }

    finally:
        app.dependency_overrides.pop(get_db, None)