from datetime import date
from decimal import Decimal
from typing import Literal
from pydantic import BaseModel, Field


class Evidence(BaseModel):
    filename: str
    page: int | None = Field(default=None, ge=1)
    text: str | None = None
    field_name: str | None = None
    extracted_value: str | None = None
    source: Literal["extracted_data", "pdf_text", "ocr"] | None = None


class Item(BaseModel):
    description: str
    product_code: str | None = None
    model: str | None = None
    quantity: Decimal | None = None
    unit: str | None = None
    hs_code: str | None = None
    origin: str | None = None
    unit_price: Decimal | None = None
    amount: Decimal | None = None
    evidence: Evidence | None = None

class Invoice(BaseModel):
    document_type: Literal['invoice'] = 'invoice'
    invoice_number: str | None = None
    invoice_date: date | None = None
    exporter: str | None = None
    consignee: str | None = None
    currency: str | None = None
    incoterm: str | None = None
    freight: Decimal | None = None
    total: Decimal | None = None
    items: list[Item] = Field(default_factory=list)

class PackingList(BaseModel):
    document_type: Literal['packing_list'] = 'packing_list'
    invoice_number: str | None = None
    consignee: str | None = None
    package_count: int | None = None
    net_weight_kg: Decimal | None = None
    gross_weight_kg: Decimal | None = None
    items: list[Item] = Field(default_factory=list)

class AirWaybill(BaseModel):
    document_type: Literal['air_waybill'] = 'air_waybill'
    awb_number: str | None = None
    shipper: str | None = None
    consignee: str | None = None
    origin_airport: str | None = None
    destination_airport: str | None = None
    package_count: int | None = None
    gross_weight_kg: Decimal | None = None
    chargeable_weight_kg: Decimal | None = None
    issue_date: date | None = None

class NMRARegistration(BaseModel):
    document_type: Literal['nmra_registration'] = 'nmra_registration'
    registration_number: str | None = None
    device_name: str | None = None
    brand: str | None = None
    models: list[str] = Field(default_factory=list)
    manufacturer: str | None = None
    importer: str | None = None
    issue_date: date | None = None
    valid_from: date | None = None
    valid_until: date | None = None
    conditions: list[str] = Field(default_factory=list)

class NMRAImportLicence(BaseModel):
    document_type: Literal['nmra_import_licence'] = 'nmra_import_licence'
    licence_number: str | None = None
    importer: str | None = None
    registration_numbers: list[str] = Field(default_factory=list)
    device_names: list[str] = Field(default_factory=list)
    issue_date: date | None = None
    valid_from: date | None = None
    valid_until: date | None = None
    conditions: list[str] = Field(default_factory=list)

class Finding(BaseModel):
    rule_code: str
    status: Literal['PASS', 'REVIEW', 'FAIL', 'NOT_VERIFIED']
    message: str
    evidence: list[Evidence] = Field(default_factory=list)

class ChatRequest(BaseModel):
    document_id: int = Field(gt=0)
    question: str = Field(min_length=1, max_length=2000)