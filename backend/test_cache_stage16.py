import json
import tempfile
from pathlib import Path
from unittest.mock import patch

from app import cache

with tempfile.TemporaryDirectory() as temp_dir:
    with patch.object(cache, "CACHE_DIR", Path(temp_dir)):

        # Test a newly saved Gemini result
        cache.save_cached_result(
            "test_gemini",
            {"invoice_number": "TEST-001"},
            source="gemini_live",
        )

        result = cache.get_cached_result("test_gemini")

        assert result["source"] == "gemini_live"
        assert result["extracted_data"]["invoice_number"] == "TEST-001"

        print("New Gemini cache: PASS")

        # Test an older cache without source metadata
        legacy_file = Path(temp_dir) / "test_legacy.json"

        legacy_file.write_text(
            json.dumps({"invoice_number": "OLD-001"}),
            encoding="utf-8",
        )

        legacy_result = cache.get_cached_result("test_legacy")

        assert legacy_result["source"] == "unknown_legacy"
        assert legacy_result["extracted_data"]["invoice_number"] == "OLD-001"

        print("Legacy cache: PASS")

        # Test synthetic data labeling
        cache.save_cached_result(
            "test_synthetic",
            {"invoice_number": "FAKE-001"},
            source="synthetic_test",
        )

        synthetic_result = cache.get_cached_result("test_synthetic")

        assert synthetic_result["source"] == "synthetic_test"

        print("Synthetic cache: PASS")

print("All Stage 16 cache tests passed!")
