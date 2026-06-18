from __future__ import annotations

import json
from pathlib import Path
from typing import Literal

from pydantic import BaseModel

from dataproduct_kit.config import KitConfig
from dataproduct_kit.models import (
    ContractManifest,
    DataProductManifest,
    PolicyManifest,
    SemanticManifest,
)

SchemaName = Literal["dataproduct", "contract", "semantic", "policy", "config", "all"]

SCHEMA_MODELS: dict[str, type[BaseModel]] = {
    "dataproduct": DataProductManifest,
    "contract": ContractManifest,
    "semantic": SemanticManifest,
    "policy": PolicyManifest,
    "config": KitConfig,
}


def build_schema(name: str) -> dict[str, object]:
    model = SCHEMA_MODELS.get(name)
    if model is None:
        raise ValueError(f"unknown schema '{name}'")
    return model.model_json_schema(by_alias=True)


def build_all_schemas() -> dict[str, dict[str, object]]:
    return {name: build_schema(name) for name in SCHEMA_MODELS}


def write_schema_files(output_dir: Path) -> list[Path]:
    output_dir.mkdir(parents=True, exist_ok=True)
    written: list[Path] = []
    for name, schema in build_all_schemas().items():
        path = output_dir / f"{name}.schema.json"
        path.write_text(json.dumps(schema, indent=2, sort_keys=True) + "\n", encoding="utf-8")
        written.append(path)
    return written
