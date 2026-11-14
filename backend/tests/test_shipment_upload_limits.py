import pytest

from app.main import app
from fastapi.testclient import TestClient


@pytest.fixture
def client(legacy_authenticated_client):
    return legacy_authenticated_client


@pytest.mark.parametrize(
    "oversized_field, expected_document_type",
    [
        ("invoice_file", "invoice"),
        ("packing_list_file", "packing_list"),
        ("air_waybill_file", "air_waybill"),
    ],
)
def test_shipment_rejects_oversized_pdf(
    client,
    oversized_field,
    expected_document_type,
    monkeypatch,
):
    import app.main as main_module

    oversized_pdf = b"%PDF-1.4\n" + b"A" * (10 * 1024 * 1024)

    # Prevent any real PDF parsing if an earlier document is processed.
    class FakeDocument:
        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc_value, traceback):
            return False

        def __len__(self):
            return 1

        def __iter__(self):
            return iter([])

    monkeypatch.setattr(
        main_module.pymupdf,
        "open",
        lambda *args, **kwargs: FakeDocument(),
    )

    files = {
        field: (
            f"{field}.pdf",
            oversized_pdf if field == oversized_field else b"%PDF-1.4\n",
            "application/pdf",
        )
        for field in (
            "invoice_file",
            "packing_list_file",
            "air_waybill_file",
        )
    }

    response = client.post(
        "/shipments/upload-and-verify",
        files=files,
    )

    assert response.status_code == 413
    assert expected_document_type in response.json()["detail"]
