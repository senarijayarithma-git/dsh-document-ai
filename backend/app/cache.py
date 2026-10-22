
import hashlib
import json
from pathlib import Path


# Location of the cache folder
CACHE_DIR = Path(__file__).resolve().parent.parent / "cache"

CACHE_DIR.mkdir(parents=True, exist_ok=True)


def generate_cache_key(
    file_bytes: bytes,
    document_type: str,
) -> str:
    """
    Create a unique identifier using the PDF
    contents and document type.
    """
    content = document_type.encode("utf-8") + b"\0" + file_bytes

    return hashlib.sha256(content).hexdigest()


def get_cached_result(cache_key: str):
    """
    Retrieve cached extraction data and its source.
    Supports both new and legacy cache formats.
    """
    cache_file = CACHE_DIR / f"{cache_key}.json"

    if not cache_file.exists():
        return None

    with cache_file.open("r", encoding="utf-8") as file:
        cached = json.load(file)

    # New cache format
    if (
        isinstance(cached, dict)
        and "source" in cached
        and "extracted_data" in cached
    ):
        return cached

    # Old cache format: origin cannot be trusted
    return {
        "source": "unknown_legacy",
        "extracted_data": cached,
    }


def save_cached_result(
    cache_key: str,
    extracted_data: dict,
    source: str,
):
    """
    Save extracted data with its original source.
    """

    allowed_sources = {
        "gemini_live",
        "synthetic_test",
    }

    if source not in allowed_sources:
        raise ValueError(f"Invalid extraction source: {source}")

    cache_file = CACHE_DIR / f"{cache_key}.json"

    cache_record = {
        "source": source,
        "extracted_data": extracted_data,
    }

    with cache_file.open("w", encoding="utf-8") as file:
        json.dump(
            cache_record,
            file,
            indent=4,
            ensure_ascii=False,
        )