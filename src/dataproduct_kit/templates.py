from __future__ import annotations

import shutil
from importlib import resources
from pathlib import Path


def scaffold_template(destination: Path, template: str) -> None:
    if template != "saas-churn":
        raise ValueError(f"unknown template '{template}'")
    source = resources.files("dataproduct_kit") / "templates" / "saas_churn"
    destination.mkdir(parents=True, exist_ok=True)
    for item in source.rglob("*"):
        relative = item.relative_to(source)
        target = destination / relative
        if item.is_dir():
            target.mkdir(parents=True, exist_ok=True)
        else:
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(item, target)
