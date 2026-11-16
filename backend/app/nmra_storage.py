
import os
import uuid
from pathlib import Path


class NMRAStorageError(Exception):
    pass


def get_storage_root() -> Path:
    configured = os.getenv("NMRA_STORAGE_DIR")

    if not configured:
        raise NMRAStorageError(
            "NMRA_STORAGE_DIR is not configured"
        )

    root = Path(configured).resolve()
    root.mkdir(parents=True, exist_ok=True)
    return root


def save_private_pdf(data: bytes) -> str:
    """Save a PDF using a random, non-user-controlled key."""

    root = get_storage_root()
    key = f"{uuid.uuid4().hex}.pdf"
    destination = root / key

    try:
        with destination.open("xb") as file:
            file.write(data)
    except OSError as exc:
        raise NMRAStorageError(
            "Unable to store NMRA PDF"
        ) from exc

    return key


def delete_private_pdf(key: str) -> None:
    """Remove a stored PDF, used for upload rollback."""

    if (
        not key
        or Path(key).name != key
        or not key.endswith(".pdf")
    ):
        raise NMRAStorageError("Invalid storage key")

    destination = get_storage_root() / key

    try:
        destination.unlink(missing_ok=True)
    except OSError as exc:
        raise NMRAStorageError(
            "Unable to remove NMRA PDF"
        ) from exc
