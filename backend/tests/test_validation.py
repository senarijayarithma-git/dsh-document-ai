from decimal import Decimal
from app.schemas import Invoice, PackingList, AirWaybill
from app.validation import validate_shipment

def test_sample_weight_mismatch():
    invoice = Invoice(invoice_number='EXPBLRDX09102602', consignee='Sunshine Healthcare Lanka Ltd.')
    packing = PackingList(invoice_number='EXPBLRDX09102602', consignee='Sunshine Healthcare Lanka Ltd.', package_count=3, gross_weight_kg=Decimal('30'))
    awb = AirWaybill(consignee='Sunshine Healthcare Lanka Ltd.', package_count=3, gross_weight_kg=Decimal('19'))
    findings = {f.rule_code: f for f in validate_shipment(invoice, packing, awb)}
    assert findings['REF-001'].status == 'PASS'
    assert findings['PKG-001'].status == 'PASS'
    assert findings['WGT-001'].status == 'REVIEW'
    assert '11 kg' in findings['WGT-001'].message
    assert findings['REG-001'].status == 'NOT_VERIFIED'
