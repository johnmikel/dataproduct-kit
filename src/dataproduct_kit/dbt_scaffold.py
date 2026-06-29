from __future__ import annotations

import json
import re
from json import JSONDecodeError
from pathlib import Path
from typing import Any

import yaml


def scaffold_from_dbt_manifest(manifest_path: Path, model: str, out: Path) -> None:
    if not manifest_path.exists():
        raise ValueError(f"dbt manifest not found: {manifest_path}")
    try:
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    except JSONDecodeError as error:
        raise ValueError(f"Invalid dbt manifest JSON: {manifest_path}") from error

    node = _find_model_node(manifest, model)
    if node is None:
        raise ValueError(f"dbt model not found: {model}")

    dataset_id = _safe_name(str(node.get("name") or model))
    out.mkdir(parents=True, exist_ok=True)
    (out / "data").mkdir(parents=True, exist_ok=True)

    _write_yaml(out / "dataproduct.yaml", _product_payload(dataset_id, node))
    _write_yaml(out / "contract.yaml", _contract_payload(dataset_id, node))
    _write_yaml(out / "semantic.yaml", {"metrics": [], "dimensions": [], "entities": []})
    _write_yaml(out / "policy.yaml", _policy_payload())


def _find_model_node(manifest: dict[str, Any], model: str) -> dict[str, Any] | None:
    nodes = manifest.get("nodes")
    if not isinstance(nodes, dict):
        return None
    for unique_id, node in nodes.items():
        if not isinstance(node, dict):
            continue
        if node.get("resource_type") != "model":
            continue
        if model in {unique_id, node.get("name"), node.get("alias")}:
            return node
    return None


def _product_payload(dataset_id: str, node: dict[str, Any]) -> dict[str, Any]:
    description = str(node.get("description") or "TODO: Describe this data product.")
    return {
        "id": dataset_id,
        "name": _title_name(dataset_id),
        "domain": "TODO",
        "version": "0.1.0",
        "description": description,
        "owner": {
            "name": "TODO",
            "email": "todo@example.com",
            "team": "TODO",
        },
        "datasets": [
            {
                "id": dataset_id,
                "path": str(Path("data") / f"{dataset_id}.csv"),
                "format": "csv",
                "table": str(node.get("alias") or node.get("name") or dataset_id),
            }
        ],
    }


def _contract_payload(dataset_id: str, node: dict[str, Any]) -> dict[str, Any]:
    columns = node.get("columns") or {}
    if not isinstance(columns, dict):
        columns = {}
    return {
        "version": "0.1",
        "dataset": dataset_id,
        "schema": [_field_payload(column_name, column) for column_name, column in columns.items()],
        "quality_checks": [
            {"name": "row_count_min", "type": "row_count_min", "value": 0},
        ],
    }


def _field_payload(column_name: str, column: Any) -> dict[str, Any]:
    if not isinstance(column, dict):
        column = {}
    payload = {
        "name": str(column.get("name") or column_name),
        "type": _map_dbt_type(column.get("data_type")),
        "nullable": True,
        "classification": _classification(column),
    }
    description = column.get("description")
    if description:
        payload["description"] = str(description)
    return payload


def _classification(column: dict[str, Any]) -> str:
    meta = column.get("meta") or {}
    if isinstance(meta, dict) and meta.get("classification"):
        return str(meta["classification"])
    return "TODO"


def _map_dbt_type(data_type: Any) -> str:
    normalized = str(data_type or "").lower()
    if any(token in normalized for token in ("int", "bigint", "smallint")):
        return "integer"
    if any(token in normalized for token in ("numeric", "decimal", "double", "float", "real")):
        return "number"
    if "bool" in normalized:
        return "boolean"
    if "timestamp" in normalized or "datetime" in normalized:
        return "timestamp"
    if normalized == "date":
        return "date"
    return "string"


def _policy_payload() -> dict[str, Any]:
    return {
        "allowed_purposes": ["TODO"],
        "access_notes": "TODO: Define allowed users, purposes, and access constraints.",
        "sensitive_fields": [],
        "agent_constraints": [],
        "bi_constraints": [],
    }


def _safe_name(value: str) -> str:
    normalized = re.sub(r"[^a-z0-9]+", "_", value.lower()).strip("_")
    return normalized or "dataset"


def _title_name(value: str) -> str:
    return f"{value.replace('_', ' ').title()} Data Product"


def _write_yaml(path: Path, payload: dict[str, Any]) -> None:
    path.write_text(yaml.safe_dump(payload, sort_keys=False), encoding="utf-8")
