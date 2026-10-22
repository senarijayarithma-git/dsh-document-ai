
from pathlib import Path

from app.cache import (
    generate_cache_key,
    save_cached_result,
)

# Fictional test documents and their expected information
documents = {
    "invoice": {
        "filename": "test_invoice.pdf",
        "data": {
            "invoice_number": "TEST-001",
            "exporter": "ABC Medical Supplies",
            "consignee": "Example Healthcare Importer",
            "currency": "USD",
            "items": [
                {
                    "product": "Medical Gloves",
                    "quantity": 100,
                    "unit_price": 5,
                    "amount": 500
                }
            ],
            "total_amount": 500
        }
    },
    "packing_list": {
        "filename": "test_packing_list.pdf",
        "data": {
            "packing_list_number": "PL-001",
            "invoice_number": "TEST-001",
            "exporter": "ABC Medical Supplies",
            "consignee": "Example Healthcare Importer",
            "items": [
                {
                    "product": "Medical Gloves",
                    "quantity": 100,
                    "unit": "boxes"
                }
            ],
            "total_packages": 5,
            "net_weight_kg": 45,
            "gross_weight_kg": 50
        }
    },
    "air_waybill": {
        "filename": "test_air_waybill.pdf",
        "data": {
            "awb_number": "123-45678901",
            "shipper": "ABC Medical Supplies",
            "consignee": "Example Healthcare Importer",
            "airport_of_departure": "CMB",
            "airport_of_destination": "SIN",
            "number_of_pieces": 5,
            "gross_weight_kg": 50,
            "chargeable_weight_kg": 50
        }
    }
}

for document_type, document in documents.items():
    filename = document["filename"]
    path = Path(__file__).resolve().parent / filename

    if not path.is_file():
        print(f"FILE NOT FOUND: {filename}")
        continue

    file_bytes = path.read_bytes()

    cache_key = generate_cache_key(
        file_bytes,
        document_type,
    )

    save_cached_result(
        cache_key,
        document["data"],
        source="synthetic_test",
    )

    print(f"Cache prepared: {filename}")

print("Finished preparing test caches!")
