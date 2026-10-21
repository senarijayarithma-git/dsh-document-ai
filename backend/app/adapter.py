
from decimal import Decimal
from .schemas import (
    Invoice,
    PackingList,
    AirWaybill,
    Item,
)


def to_decimal(value):
    if value is None:
        return None
    return Decimal(str(value))


def convert_invoice(data: dict) -> Invoice:
    items = []

    for item in data.get("items", []):
        items.append(
            Item(
                description=item["product"],
                quantity=to_decimal(item.get("quantity")),
                unit_price=to_decimal(item.get("unit_price")),
                amount=to_decimal(item.get("amount")),
            )
        )

    return Invoice(
        invoice_number=data.get("invoice_number"),
        invoice_date=data.get("invoice_date"),
        exporter=data.get("exporter"),
        consignee=data.get("consignee"),
        currency=data.get("currency"),
        freight=to_decimal(data.get("freight")),
        total=to_decimal(data.get("total_amount")),
        items=items,
    )


def convert_packing_list(data: dict) -> PackingList:
    items = []

    for item in data.get("items", []):
        items.append(
            Item(
                description=item["product"],
                quantity=to_decimal(item.get("quantity")),
                unit=item.get("unit"),
            )
        )

    return PackingList(
        invoice_number=data.get("invoice_number"),
        consignee=data.get("consignee"),
        package_count=(
            data.get("total_packages")
            if data.get("total_packages") is not None
            else data.get("total_cartons")
        ),
        net_weight_kg=to_decimal(data.get("net_weight_kg")),
        gross_weight_kg=to_decimal(data.get("gross_weight_kg")),
        items=items,
    )


def convert_air_waybill(data: dict) -> AirWaybill:
    return AirWaybill(
        awb_number=data.get("awb_number"),
        shipper=data.get("shipper"),
        consignee=data.get("consignee"),
        origin_airport=data.get("airport_of_departure"),
        destination_airport=data.get("airport_of_destination"),
        package_count=data.get("number_of_pieces"),
        gross_weight_kg=to_decimal(data.get("gross_weight_kg")),
        chargeable_weight_kg=to_decimal(
            data.get("chargeable_weight_kg")
        ),
        issue_date=data.get("awb_date"),
    )
