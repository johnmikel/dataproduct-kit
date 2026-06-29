from __future__ import annotations

from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[1]


def test_scaffold_from_dbt_manifest_writes_starter_manifests(tmp_path: Path) -> None:
    from dataproduct_kit.dbt_scaffold import scaffold_from_dbt_manifest

    manifest = ROOT / "tests/fixtures/dbt/manifest.json"
    out = tmp_path / "data-products/fct-orders"

    scaffold_from_dbt_manifest(manifest, "fct_orders", out)

    assert (out / "dataproduct.yaml").exists()
    assert (out / "contract.yaml").exists()
    assert (out / "semantic.yaml").exists()
    assert (out / "policy.yaml").exists()

    product = yaml.safe_load((out / "dataproduct.yaml").read_text(encoding="utf-8"))
    contract = yaml.safe_load((out / "contract.yaml").read_text(encoding="utf-8"))
    semantic = yaml.safe_load((out / "semantic.yaml").read_text(encoding="utf-8"))
    policy = yaml.safe_load((out / "policy.yaml").read_text(encoding="utf-8"))

    assert product["id"] == "fct_orders"
    assert product["description"] == "Order facts for revenue and operations reporting."
    assert product["datasets"] == [
        {
            "id": "fct_orders",
            "path": "data/fct_orders.csv",
            "format": "csv",
            "table": "fct_orders",
        }
    ]
    assert contract["dataset"] == "fct_orders"
    assert contract["schema"] == [
        {
            "name": "order_id",
            "type": "string",
            "nullable": True,
            "classification": "internal",
            "description": "Stable order identifier.",
        },
        {
            "name": "ordered_at",
            "type": "timestamp",
            "nullable": True,
            "classification": "TODO",
            "description": "Timestamp when the order was placed.",
        },
        {
            "name": "net_revenue",
            "type": "number",
            "nullable": True,
            "classification": "confidential",
            "description": "Revenue after discounts and refunds.",
        },
    ]
    assert contract["quality_checks"] == [
        {"name": "row_count_min", "type": "row_count_min", "value": 0}
    ]
    assert semantic == {"metrics": [], "dimensions": [], "entities": []}
    assert policy["allowed_purposes"] == ["TODO"]
