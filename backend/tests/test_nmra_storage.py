
import pytest

from app.nmra_storage import (
    NMRAStorageError,
    delete_private_pdf,
    save_private_pdf,
)


def test_saves_pdf_with_random_filename(
    tmp_path, monkeypatch
):
    monkeypatch.setenv(
        "NMRA_STORAGE_DIR",
        str(tmp_path),
    )

    data = b"%PDF-test-document"
    key = save_private_pdf(data)

    assert key.endswith(".pdf")
    assert (tmp_path / key).read_bytes() == data
    assert key != "test-document.pdf"


def test_generates_unique_storage_keys(
    tmp_path, monkeypatch
):
    monkeypatch.setenv(
        "NMRA_STORAGE_DIR",
        str(tmp_path),
    )

    first = save_private_pdf(b"%PDF-first")
    second = save_private_pdf(b"%PDF-second")

    assert first != second


def test_deletes_stored_pdf(
    tmp_path, monkeypatch
):
    monkeypatch.setenv(
        "NMRA_STORAGE_DIR",
        str(tmp_path),
    )

    key = save_private_pdf(b"%PDF-test")

    delete_private_pdf(key)

    assert not (tmp_path / key).exists()


def test_rejects_path_traversal(
    tmp_path, monkeypatch
):
    monkeypatch.setenv(
        "NMRA_STORAGE_DIR",
        str(tmp_path),
    )

    with pytest.raises(NMRAStorageError):
        delete_private_pdf("../secret.pdf")


def test_requires_storage_configuration(
    monkeypatch,
):
    monkeypatch.delenv(
        "NMRA_STORAGE_DIR",
        raising=False,
    )

    with pytest.raises(NMRAStorageError):
        save_private_pdf(b"%PDF-test")
