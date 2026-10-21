
from decimal import Decimal
from .schemas import Invoice, PackingList, AirWaybill, Finding, Evidence


def normalise_name(value: str) -> str:
    return " ".join(
        "".join(
            c for c in value.casefold()
            if c.isalnum() or c.isspace()
        ).split()
    )


def validate_shipment(
    invoice: Invoice,
    packing: PackingList,
    awb: AirWaybill,
    packing_filename: str = "unknown_packing_list.pdf",
    awb_filename: str = "unknown_air_waybill.pdf",
    invoice_filename: str = "unknown_invoice.pdf",
) -> list[Finding]:

    results: list[Finding] = []

    def add(code, status, message, evidence=None):
        results.append(
            Finding(
                rule_code=code,
                status=status,
                message=message,
                evidence=evidence if evidence is not None else [],
            )
        )

    def make_evidence(filename, field_name, value):
        if value is None:
            return None

        return Evidence(
            filename=filename,
            field_name=field_name,
            extracted_value=str(value),
            source="extracted_data",
        )

    def collect_evidence(*entries):
        return [entry for entry in entries if entry is not None]

    # REF-001: Invoice reference comparison
    reference_evidence = collect_evidence(
        make_evidence(
            invoice_filename,
            "invoice_number",
            invoice.invoice_number,
        ),
        make_evidence(
            packing_filename,
            "invoice_number",
            packing.invoice_number,
        ),
    )

    if invoice.invoice_number and packing.invoice_number:
        ok = (
            invoice.invoice_number.strip().upper()
            == packing.invoice_number.strip().upper()
        )

        add(
            "REF-001",
            "PASS" if ok else "REVIEW",
            "Invoice reference matches packing list"
            if ok else "Invoice references differ",
            reference_evidence,
        )
    else:
        add(
            "REF-001",
            "REVIEW",
            "Invoice reference missing in at least one document",
            reference_evidence,
        )

    # IMP-001: Consignee comparison
    consignee_evidence = collect_evidence(
        make_evidence(
            invoice_filename,
            "consignee",
            invoice.consignee,
        ),
        make_evidence(
            packing_filename,
            "consignee",
            packing.consignee,
        ),
        make_evidence(
            awb_filename,
            "consignee",
            awb.consignee,
        ),
    )

    names = [
        invoice.consignee,
        packing.consignee,
        awb.consignee,
    ]

    if all(names):
        ok = len({normalise_name(x) for x in names}) == 1

        add(
            "IMP-001",
            "PASS" if ok else "REVIEW",
            "Consignee names match exactly after basic normalization"
            if ok else "Consignee names require review",
            consignee_evidence,
        )
    else:
        add(
            "IMP-001",
            "REVIEW",
            "Consignee missing in at least one document",
            consignee_evidence,
        )

    # WGT-001: Gross weight comparison
    weight_evidence = collect_evidence(
        make_evidence(
            packing_filename,
            "gross_weight_kg",
            packing.gross_weight_kg,
        ),
        make_evidence(
            awb_filename,
            "gross_weight_kg",
            awb.gross_weight_kg,
        ),
    )

    if (
        packing.gross_weight_kg is not None
        and awb.gross_weight_kg is not None
    ):
        diff = abs(
            packing.gross_weight_kg - awb.gross_weight_kg
        )

        add(
            "WGT-001",
            "PASS" if diff == Decimal("0") else "REVIEW",
            f"Packing list gross weight {packing.gross_weight_kg} kg; "
            f"AWB gross weight {awb.gross_weight_kg} kg; "
            f"difference {diff} kg",
            weight_evidence,
        )
    else:
        add(
            "WGT-001",
            "REVIEW",
            "Gross weight missing from packing list or AWB",
            weight_evidence,
        )

    # PKG-001: Package count comparison
    package_evidence = collect_evidence(
        make_evidence(
            packing_filename,
            "package_count",
            packing.package_count,
        ),
        make_evidence(
            awb_filename,
            "package_count",
            awb.package_count,
        ),
    )

    if (
        packing.package_count is not None
        and awb.package_count is not None
    ):
        ok = packing.package_count == awb.package_count

        add(
            "PKG-001",
            "PASS" if ok else "REVIEW",
            f"Packing list {packing.package_count} packages; "
            f"AWB {awb.package_count} packages",
            package_evidence,
        )
    else:
        add(
            "PKG-001",
            "REVIEW",
            "Package count missing from packing list or AWB",
            package_evidence,
        )

    
    # WGT-002: Gross weight must not be less than net weight
    weight_consistency_evidence = collect_evidence(
        make_evidence(
            packing_filename,
            "net_weight_kg",
            packing.net_weight_kg,
        ),
        make_evidence(
            packing_filename,
            "gross_weight_kg",
            packing.gross_weight_kg,
        ),
    )

    if (
        packing.net_weight_kg is not None
        and packing.gross_weight_kg is not None
    ):
        weight_ok = (
            packing.gross_weight_kg >= packing.net_weight_kg
        )

        add(
            "WGT-002",
            "PASS" if weight_ok else "REVIEW",
            "Gross weight is greater than or equal to net weight"
            if weight_ok
            else "Gross weight is less than net weight",
            weight_consistency_evidence,
        )
    else:
        add(
            "WGT-002",
            "REVIEW",
            "Net weight or gross weight is missing from packing list",
            weight_consistency_evidence,
        )

    
    # INV-001: Check invoice total against item amounts
    invoice_total_evidence = collect_evidence(
        make_evidence(
            invoice_filename,
            "total",
            invoice.total,
        ),
    )

    item_amounts = [
        item.amount for item in invoice.items
    ]

    for index, item in enumerate(invoice.items, start=1):
        invoice_total_evidence.extend(
            collect_evidence(
                make_evidence(
                    invoice_filename,
                    f"items[{index - 1}].amount",
                    item.amount,
                )
            )
        )

    if (
        invoice.total is not None
        and item_amounts
        and all(amount is not None for amount in item_amounts)
    ):
        calculated_total = sum(item_amounts, Decimal("0"))
        difference = abs(invoice.total - calculated_total)

        add(
            "INV-001",
            "PASS" if difference <= Decimal("0.01") else "REVIEW",
            f"Invoice total {invoice.total}; "
            f"sum of item amounts {calculated_total}; "
            f"difference {difference}",
            invoice_total_evidence,
        )
    else:
        add(
            "INV-001",
            "REVIEW",
            "Invoice total or item amounts are missing",
            invoice_total_evidence,
        )

    # REG-001: NMRA verification
    add(
        "REG-001",
        "NOT_VERIFIED",
        "Product-level NMRA coverage requires approved matching "
        "rules, referenced attachments and authoritative "
        "status verification",
    )

    return results