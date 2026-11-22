
from app.nmra_item_extraction import (
    extract_attachment_items,
)


def test_extract_attachment_items_deduplicates(monkeypatch):
    class FakePage:
        pass

    class FakeDocument:
        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc, tb):
            return False

        def __iter__(self):
            return iter([FakePage(), FakePage()])

    def fake_open(_path):
        return FakeDocument()

    def fake_extract(_page, page_number):
        return [
            {
                "item_code": "BLT00001",
                "product_description": None,
                "page_number": page_number,
                "row_number": 1,
                "evidence_text": "1 BLT00001",
                "extraction_method": "OCR",
                "review_status": "UNREVIEWED",
            },
            {
                "item_code": "BLT00001",
                "product_description": None,
                "page_number": page_number,
                "row_number": 1,
                "evidence_text": "1 BLT00001",
                "extraction_method": "OCR",
                "review_status": "UNREVIEWED",
            },
        ]

    monkeypatch.setattr(
        "app.nmra_item_extraction.pymupdf.open",
        fake_open,
    )
    monkeypatch.setattr(
        "app.nmra_item_extraction.extract_page_items",
        fake_extract,
    )

    items = extract_attachment_items("test.pdf")

    assert len(items) == 2
    assert [item["page_number"] for item in items] == [1, 2]
    assert all(
        item["review_status"] == "UNREVIEWED"
        for item in items
    )


def test_code_pattern_accepts_expected_codes():
    from app.nmra_item_extraction import CODE_PATTERN

    assert CODE_PATTERN.fullmatch("BLT00001")
    assert CODE_PATTERN.fullmatch("XSYS0001")
    assert not CODE_PATTERN.fullmatch("INVALID123")
