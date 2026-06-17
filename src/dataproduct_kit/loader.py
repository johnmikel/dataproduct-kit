from __future__ import annotations

from pathlib import Path
from typing import Any, TypeVar

import yaml
from pydantic import BaseModel, ValidationError

from dataproduct_kit.models import (
    ContractManifest,
    DataProductManifest,
    DataProductProject,
    PolicyManifest,
    SemanticManifest,
)


class ManifestLoadError(ValueError):
    """Raised when a data product manifest cannot be parsed or validated."""


ModelT = TypeVar("ModelT", bound=BaseModel)


def load_project(root: Path | str) -> DataProductProject:
    root_path = Path(root)
    product = _load_model(root_path, "dataproduct.yaml", DataProductManifest)
    contract = _load_model(root_path, "contract.yaml", ContractManifest)
    semantic = _load_model(root_path, "semantic.yaml", SemanticManifest)
    policy = _load_model(root_path, "policy.yaml", PolicyManifest)
    return DataProductProject(
        root=root_path,
        product=product,
        contract=contract,
        semantic=semantic,
        policy=policy,
    )


def _load_model(root: Path, filename: str, model: type[ModelT]) -> ModelT:
    data = _read_yaml(root / filename, filename)
    try:
        return model.model_validate(data)
    except ValidationError as error:
        messages = [_format_validation_error(filename, item) for item in error.errors()]
        raise ManifestLoadError("; ".join(messages)) from error


def _read_yaml(path: Path, filename: str) -> dict[str, Any]:
    if not path.exists():
        raise ManifestLoadError(f"{filename}: file not found")
    try:
        data = yaml.safe_load(path.read_text(encoding="utf-8"))
    except yaml.YAMLError as error:
        raise ManifestLoadError(f"{filename}: YAML parse error: {error}") from error
    if not isinstance(data, dict):
        raise ManifestLoadError(f"{filename}: expected a YAML mapping")
    return data


def _format_validation_error(filename: str, item: dict[str, Any]) -> str:
    loc = ".".join(str(part) for part in item["loc"])
    return f"{filename}: {loc}: {item['msg']}"
