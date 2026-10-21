
from datetime import datetime, timezone


def build_verification_report(findings):
    """
    Convert verification findings into a
    structured, readable report.
    """

    report = {
        "report_title": "DSH Document AI Verification Report",
        "generated_at": datetime.now(
            timezone.utc
        ).isoformat(),
        "total_checks": len(findings),
        "summary": {
            "passed": 0,
            "needs_review": 0,
            "failed": 0,
            "not_verified": 0,
        },
        "findings": [],
    }

    for finding in findings:
        if finding.status == "PASS":
            report["summary"]["passed"] += 1

        elif finding.status == "REVIEW":
            report["summary"]["needs_review"] += 1

        elif finding.status == "FAIL":
            report["summary"]["failed"] += 1

        elif finding.status == "NOT_VERIFIED":
            report["summary"]["not_verified"] += 1

        report["findings"].append({
            "rule_code": finding.rule_code,
            "status": finding.status,
            "message": finding.message,
            "evidence": [
                evidence.model_dump(mode="json")
                for evidence in finding.evidence
            ],
        })

    return report
