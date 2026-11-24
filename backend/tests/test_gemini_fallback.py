from types import SimpleNamespace
from unittest.mock import MagicMock

from google.genai import errors

from app import ai_extraction


def test_fallback_after_primary_model_503(monkeypatch):
    monkeypatch.setenv("GEMINI_API_KEY", "fake-test-key")
    monkeypatch.setattr(ai_extraction.time, "sleep", lambda _: None)

    response = SimpleNamespace(
        text='{"invoice_number": "INV-TEST-001", "items": []}'
    )

    mock_client = MagicMock()
    mock_client.models.generate_content.side_effect = [
        errors.ServerError(
            503,
            {
                "error": {
                    "code": 503,
                    "message": "Model overloaded",
                    "status": "UNAVAILABLE",
                }
            },
        ),
        errors.ServerError(
            503,
            {
                "error": {
                    "code": 503,
                    "message": "Model overloaded",
                    "status": "UNAVAILABLE",
                }
            },
        ),
        errors.ServerError(
            503,
            {
                "error": {
                    "code": 503,
                    "message": "Model overloaded",
                    "status": "UNAVAILABLE",
                }
            },
        ),
        response,
    ]

    monkeypatch.setattr(
        ai_extraction.genai,
        "Client",
        lambda **kwargs: mock_client,
    )

    result = ai_extraction.extract_structured_data(
        text="Invoice number: INV-TEST-001",
        document_type="invoice",
    )

    assert result.invoice_number == "INV-TEST-001"

    called_models = [
        call.kwargs["model"]
        for call in mock_client.models.generate_content.call_args_list
    ]

    assert called_models == [
        "gemini-3.8-flash",
        "gemini-3.8-flash",
        "gemini-3.8-flash",
        "gemini-3.5-flash",
    ]