from app.adapter import convert_invoice


def test_invoice_item_code_maps_to_product_code():
    invoice = convert_invoice({
        "items": [
            {
                "product": "Test Product",
                "item_code": "NMRA-TEST-001",
            }
        ]
    })

    assert invoice.items[0].product_code == "NMRA-TEST-001"


def test_explicit_product_code_takes_priority():
    invoice = convert_invoice({
        "items": [
            {
                "product": "Test Product",
                "product_code": "EXPLICIT-001",
                "item_code": "FALLBACK-001",
            }
        ]
    })

    assert invoice.items[0].product_code == "EXPLICIT-001"


def test_supplier_material_code_is_not_assumed_to_be_nmra_code():
    invoice = convert_invoice({
        "items": [
            {
                "product": "Test Product",
                "material_code": "SUPPLIER-001",
            }
        ]
    })

    assert invoice.items[0].product_code is None
