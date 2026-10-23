
from fastapi.testclient import TestClient
from app.main import app


client = TestClient(app)


def test_shipment_validation_endpoint():
    shipment_data = {
        "invoice": {
            "invoice_number": "INV-001",
            "consignee": "ABC Imports",
            "total": 5000,
            "currency": "USD",
            "items": [
                {
                    "description": "Electronic Components",
                    "quantity": 100
                }
            ]
        },
        "packing_list": {
            "invoice_number": "INV-001",
            "consignee": "ABC Imports",
            "package_count": 10,
            "net_weight_kg": 90,
            "gross_weight_kg": 100,
            "items": [
                {
                    "description": "Electronic Components",
                    "quantity": 100
                }
            ]
        },
        "air_waybill": {
            "awb_number": "123-45678901",
            "consignee": "ABC Imports",
            "package_count": 10,
            "gross_weight_kg": 100
        }
    }

    response = client.post(
        "/shipments/validate",
        json=shipment_data
    )

    assert response.status_code == 200
    assert "findings" in response.json()
    assert isinstance(response.json()["findings"], list)

    
def test_shipment_weight_mismatch_api():
    shipment_data = {
        "invoice": {
            "invoice_number": "EXPBLRDX09102602",
            "consignee": "Sunshine Healthcare Lanka Ltd."
        },
        "packing_list": {
            "invoice_number": "EXPBLRDX09102602",
            "consignee": "Sunshine Healthcare Lanka Ltd.",
            "package_count": 3,
            "gross_weight_kg": 30
        },
        "air_waybill": {
            "consignee": "Sunshine Healthcare Lanka Ltd.",
            "package_count": 3,
            "gross_weight_kg": 19
        }
    }

    response = client.post(
        "/shipments/validate",
        json=shipment_data
    )

    assert response.status_code == 200

    findings = {
        finding["rule_code"]: finding
        for finding in response.json()["findings"]
    }

    assert findings["REF-001"]["status"] == "PASS"
    assert findings["PKG-001"]["status"] == "PASS"
    assert findings["WGT-001"]["status"] == "REVIEW"
    assert "11 kg" in findings["WGT-001"]["message"]
    assert findings["REG-001"]["status"] == "NOT_VERIFIED"


def test_shipment_validation_missing_air_waybill():
    shipment_data = {
        "invoice": {
            "invoice_number": "INV-001",
            "consignee": "ABC Imports"
        },
        "packing_list": {
            "invoice_number": "INV-001",
            "consignee": "ABC Imports",
            "package_count": 10
        }
    }

    response = client.post(
        "/shipments/validate",
        json=shipment_data
    )

    assert response.status_code == 422

    errors = response.json()["detail"]

    assert any(
        error["loc"] == ["body", "air_waybill"]
        for error in errors
    )

def test_shipment_validation_invalid_package_count():
    shipment_data = {
        "invoice": {
            "invoice_number": "INV-001"
        },
        "packing_list": {
            "invoice_number": "INV-001",
            "package_count": "ten"
        },
        "air_waybill": {
            "awb_number": "123-45678901",
            "package_count": 10
        }
    }

    response = client.post(
        "/shipments/validate",
        json=shipment_data
    )

    assert response.status_code == 422

    errors = response.json()["detail"]

    assert any(
        error["loc"] == ["body", "packing_list", "package_count"]
        for error in errors
    )

def test_shipment_validation_invalid_package_count():
    shipment_data = {
        "invoice": {
            "invoice_number": "INV-001"
        },
        "packing_list": {
            "invoice_number": "INV-001",
            "package_count": "ten"
        },
        "air_waybill": {
            "awb_number": "123-45678901",
            "package_count": 10
        }
    }

    response = client.post(
        "/shipments/validate",
        json=shipment_data
    )

    assert response.status_code == 422

    errors = response.json()["detail"]

    assert any(
        error["loc"] == ["body", "packing_list", "package_count"]
        for error in errors
    )
