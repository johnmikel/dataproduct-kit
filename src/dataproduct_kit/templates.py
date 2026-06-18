from __future__ import annotations

import shutil
from importlib import resources
from pathlib import Path


TEMPLATE_MAP = {
    "saas-churn": "saas_churn",
    "finance-revenue": "finance_revenue",
}


def scaffold_template(destination: Path, template: str) -> None:
    dir_name = TEMPLATE_MAP.get(template)
    if dir_name is None:
        raise ValueError(f"unknown template '{template}'")
    source = resources.files("dataproduct_kit") / "templates" / dir_name
    destination.mkdir(parents=True, exist_ok=True)
    for item in source.rglob("*"):
        relative = item.relative_to(source)
        target = destination / relative
        if item.is_dir():
            target.mkdir(parents=True, exist_ok=True)
        else:
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(item, target)
