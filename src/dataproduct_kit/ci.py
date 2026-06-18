from __future__ import annotations

import json
from collections.abc import Iterable
from pathlib import Path

from dataproduct_kit.models import Finding, ValidationSuiteReport
from dataproduct_kit.source_locations import manifest_for_code


def render_text_suite(suite: ValidationSuiteReport) -> str:
    lines = [
        f"status: {suite.status}",
        (
            "products: "
            f"{suite.summary['products_total']} total, "
            f"{suite.summary['products_passed']} passed, "
            f"{suite.summary['products_warned']} warned, "
            f"{suite.summary['products_failed']} failed"
        ),
    ]
    for finding in suite.findings:
        lines.append(f"{finding.level}: {finding.code}: {finding.message}")
    for product in suite.products:
        label = product.product_id or "unknown"
        lines.append(f"{product.status}: {product.path}: {label}")
        for finding in product.findings:
            prefix = "  suppressed" if finding.suppressed else f"  {finding.level}"
            suffix = (
                f" (suppressed until {finding.suppression_expires}: "
                f"{finding.suppression_reason})"
                if finding.suppressed
                else ""
            )
            if finding.check:
                lines.append(
                    f"{prefix}: {finding.code} ({finding.check}): {finding.message}{suffix}"
                )
            else:
                lines.append(f"{prefix}: {finding.code}: {finding.message}{suffix}")
    return "\n".join(lines) + "\n"


def render_json_suite(suite: ValidationSuiteReport) -> str:
    return json.dumps(suite.model_dump(mode="json"), indent=2, sort_keys=True) + "\n"


def render_github_annotations(suite: ValidationSuiteReport) -> str:
    lines: list[str] = []
    for product_path, finding in _iter_findings(suite):
        if finding.suppressed:
            continue
        command = "error" if finding.level == "error" else "warning"
        file_uri = _finding_uri(product_path, finding.code)
        properties = [f"file={_escape_property(file_uri)}"]
        if finding.line is not None:
            properties.append(f"line={finding.line}")
        properties.append(f"title={_escape_property(finding.code)}")
        message = _escape_message(finding.message)
        lines.append(f"::{command} {','.join(properties)}::{message}")
    if not lines:
        lines.append(f"dataproduct-kit: status {suite.status}")
    return "\n".join(lines) + "\n"


def render_sarif_report(suite: ValidationSuiteReport) -> dict:
    findings = list(_iter_findings(suite))
    rules = [
        {
            "id": code,
            "name": code,
            "shortDescription": {"text": code},
        }
        for code in sorted({finding.code for _, finding in findings})
    ]
    results = [_sarif_result(product_path, finding) for product_path, finding in findings]
    return {
        "$schema": "https://json.schemastore.org/sarif-2.1.0.json",
        "version": "2.1.0",
        "runs": [
            {
                "tool": {
                    "driver": {
                        "name": "dataproduct-kit",
                        "informationUri": "https://github.com/johnmikel/dataproduct-kit",
                        "rules": rules,
                    }
                },
                "results": results,
            }
        ],
    }


def _sarif_result(product_path: str, finding: Finding) -> dict:
    physical_location = {
        "artifactLocation": {
            "uri": _finding_uri(product_path, finding.code),
        }
    }
    if finding.line is not None:
        physical_location["region"] = {"startLine": finding.line}
    result = {
        "ruleId": finding.code,
        "level": "error" if finding.level == "error" else "warning",
        "message": {"text": finding.message},
        "locations": [
            {
                "physicalLocation": physical_location,
            }
        ],
    }
    if finding.suppressed:
        result["suppressions"] = [
            {
                "kind": "external",
                "justification": (
                    f"{finding.suppression_reason} "
                    f"Expires {finding.suppression_expires}."
                ),
            }
        ]
    return result


def write_sarif_report(suite: ValidationSuiteReport, out: Path) -> None:
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(
        json.dumps(render_sarif_report(suite), indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )


def _iter_findings(suite: ValidationSuiteReport) -> Iterable[tuple[str, Finding]]:
    for finding in suite.findings:
        yield ".", finding
    for product in suite.products:
        for finding in product.findings:
            yield product.path, finding


def _finding_uri(product_path: str, code: str) -> str:
    manifest = _manifest_for_code(code)
    if product_path == ".":
        return manifest
    return f"{product_path}/{manifest}"


def _manifest_for_code(code: str) -> str:
    return manifest_for_code(code)


def _escape_property(value: str) -> str:
    return (
        value.replace("%", "%25")
        .replace("\r", "%0D")
        .replace("\n", "%0A")
        .replace(":", "%3A")
        .replace(",", "%2C")
    )


def _escape_message(value: str) -> str:
    return value.replace("%", "%25").replace("\r", "%0D").replace("\n", "%0A")
