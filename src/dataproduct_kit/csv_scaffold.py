from __future__ import annotations

import csv
import re
import shutil
from datetime import datetime
from pathlib import Path
from typing import Any

import yaml


def scaffold_from_csv(csv_path: Path, out: Path) -> None:
    if not csv_path.exists():
        raise ValueError(f"CSV file not found: {csv_path}")
    rows = _sample_rows(csv_path)
    if not rows:
        raise ValueError(f"CSV file has no header row: {csv_path}")
    columns = list(rows[0].keys())
    dataset_id = _safe_name(csv_path.stem)
    out.mkdir(parents=True, exist_ok=True)
    data_dir = out / "data"
    data_dir.mkdir(parents=True, exist_ok=True)
    target_csv = data_dir / csv_path.name
    shutil.copyfile(csv_path, target_csv)
    _write_yaml(out / "dataproduct.yaml", _product_payload(dataset_id, target_csv))
    _write_yaml(out / "contract.yaml", _contract_payload(dataset_id, columns, rows))
    _write_yaml(out / "semantic.yaml", {"metrics": [], "dimensions": [], "entities": []})
    _write_yaml(out / "policy.yaml", _policy_payload())


def _sample_rows(csv_path: Path) -> list[dict[str, str]]:
    with csv_path.open(newline="", encoding="utf-8") as handle:
        return list(csv.DictReader(handle))[:25]


def _product_payload(dataset_id: str, target_csv: Path) -> dict[str, Any]:
    return {
        "id": dataset_id,
        "name": _title_name(dataset_id),
        "domain": "TODO",
        "version": "0.1.0",
        "description": "TODO: Describe this data product.",
        "owner": {
            "name": "TODO",
            "email": "todo@example.com",
            "team": "TODO",
        },
        "datasets": [
            {
                "id": dataset_id,
                "path": str(Path(target_csv.parent.name) / target_csv.name),
                "format": "csv",
                "table": dataset_id,
            }
        ],
    }


def _contract_payload(
    dataset_id: str,
    columns: list[str],
    rows: list[dict[str, str]],
) -> dict[str, Any]:
    return {
        "version": "0.1",
        "dataset": dataset_id,
        "schema": [
            {
                "name": column,
                "type": _infer_type([row.get(column, "") for row in rows]),
                "nullable": True,
                "classification": "TODO",
            }
            for column in columns
        ],
        "quality_checks": [
            {"name": "row_count_min", "type": "row_count_min", "value": 1},
        ],
    }


def _policy_payload() -> dict[str, Any]:
    return {
        "allowed_purposes": ["TODO"],
        "access_notes": "TODO: Define allowed users, purposes, and access constraints.",
        "sensitive_fields": [],
        "agent_constraints": [],
        "bi_constraints": [],
    }


def _infer_type(values: list[str | None]) -> str:
    populated = [value.strip() for value in values if value and value.strip()]
    if not populated:
        return "string"
    if all(_is_boolean(value) for value in populated):
        return "boolean"
    if all(_is_integer(value) for value in populated):
        return "integer"
    if all(_is_number(value) for value in populated):
        return "number"
    if all(_is_timestamp(value) for value in populated):
        return "timestamp"
    return "string"


def _safe_name(value: str) -> str:
    normalized = re.sub(r"[^a-z0-9]+", "_", value.lower()).strip("_")
    return normalized or "dataset"


def _title_name(value: str) -> str:
    return f"{value.replace('_', ' ').title()} Data Product"


def _is_boolean(value: str) -> bool:
    return value.lower() in {"true", "false"}


def _is_integer(value: str) -> bool:
    try:
        int(value)
    except ValueError:
        return False
    return True


def _is_number(value: str) -> bool:
    try:
        float(value)
    except ValueError:
        return False
    return True


def _is_timestamp(value: str) -> bool:
    try:
        datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return False
    return True


def _write_yaml(path: Path, payload: dict[str, Any]) -> None:
    path.write_text(yaml.safe_dump(payload, sort_keys=False), encoding="utf-8")
