
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
    Retrieve previously extracted JSON.
    """
    cache_file = CACHE_DIR / f"{cache_key}.json"

    if not cache_file.exists():
        return None

    with cache_file.open("r", encoding="utf-8") as file:
        return json.load(file)


def save_cached_result(
    cache_key: str,
    extracted_data: dict,
):
    """
    Save a successful extraction as JSON.
    """
    cache_file = CACHE_DIR / f"{cache_key}.json"

    with cache_file.open("w", encoding="utf-8") as file:
        json.dump(
            extracted_data,
            file,
            indent=4,
            ensure_ascii=False,
        )
