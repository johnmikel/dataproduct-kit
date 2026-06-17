from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any

from dataproduct_kit.models import DataProductProject, TrustReport


def export_odcs(project: DataProductProject) -> dict[str, Any]:
    return {
        "apiVersion": "v3.1.0-compatible",
        "kind": "DataContract",
        "id": project.product.id,
        "name": project.product.name,
        "version": project.product.version,
        "domain": project.product.domain,
        "owner": project.product.owner.model_dump(mode="json"),
        "dataset": project.contract.dataset,
        "schema": [
            {
                "name": field.name,
                "type": field.type,
                "nullable": field.nullable,
                "classification": field.classification,
            }
            for field in project.contract.schema
        ],
        "quality": [
            check.model_dump(mode="json", exclude_none=True)
            for check in project.contract.quality_checks
        ],
    }


def export_osi(project: DataProductProject) -> dict[str, Any]:
    return {
        "apiVersion": "osi-compatible-v1",
        "kind": "SemanticModel",
        "id": project.product.id,
        "name": project.product.name,
        "metrics": [metric.model_dump(mode="json") for metric in project.semantic.metrics],
        "dimensions": [
            dimension.model_dump(mode="json")
            for dimension in project.semantic.dimensions
        ],
        "entities": [entity.model_dump(mode="json") for entity in project.semantic.entities],
    }


def emit_openlineage(project: DataProductProject, report: TrustReport, output: Path) -> Path:
    output.parent.mkdir(parents=True, exist_ok=True)
    dataset = next(item for item in project.product.datasets if item.id == project.contract.dataset)
    event_time = _event_time(report)
    event = {
        "eventType": "COMPLETE",
        "eventTime": event_time,
        "producer": "https://github.com/dataproduct-kit/dataproduct-kit",
        "schemaURL": "https://openlineage.io/spec/2-0-2/OpenLineage.json",
        "run": {
            "runId": _run_id(project, report),
            "facets": {
                "dataproduct": {
                    "productId": project.product.id,
                    "version": project.product.version,
                    "status": report.status,
                }
            },
        },
        "job": {
            "namespace": "dataproduct-kit",
            "name": f"{project.product.id}.validation",
        },
        "inputs": [
            {
                "namespace": "file",
                "name": str(project.root / dataset.path),
                "facets": {
                    "schema": {
                        "fields": [
                            {"name": field.name, "type": field.type}
                            for field in project.contract.schema
                        ]
                    }
                },
            }
        ],
        "outputs": [
            {
                "namespace": "dataproduct-kit",
                "name": f"{project.product.id}.trust_report",
                "facets": {
                    "dataQualityMetrics": {
                        "rowCount": None,
                        "checksPassed": report.summary["checks_passed"],
                        "checksFailed": report.summary["checks_failed"],
                    }
                },
            }
        ],
    }
    output.write_text(json.dumps(event, sort_keys=True) + "\n", encoding="utf-8")
    return output


def _event_time(report: TrustReport) -> str:
    if report.freshness and report.freshness[0].reference_time:
        return report.freshness[0].reference_time
    return "1970-01-01T00:00:00Z"


def _run_id(project: DataProductProject, report: TrustReport) -> str:
    raw = f"{project.product.id}:{project.product.version}:{report.status}".encode()
    return hashlib.sha256(raw).hexdigest()
