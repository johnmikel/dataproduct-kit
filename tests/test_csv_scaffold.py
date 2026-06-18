from __future__ import annotations

from pathlib import Path

import yaml


def test_scaffold_from_csv_writes_starter_manifests(tmp_path: Path) -> None:
    from dataproduct_kit.csv_scaffold import scaffold_from_csv

    csv_path = tmp_path / "customers.csv"
    csv_path.write_text(
        "customer_id,email,created_at,total_spend\n"
        "cust_001,a@example.com,2026-06-01T00:00:00Z,42.5\n",
        encoding="utf-8",
    )
    out = tmp_path / "data-products/customers"

    scaffold_from_csv(csv_path, out)

    assert (out / "dataproduct.yaml").exists()
    assert (out / "contract.yaml").exists()
    assert (out / "semantic.yaml").exists()
    assert (out / "policy.yaml").exists()
    assert (out / "data/customers.csv").exists()
    product = yaml.safe_load((out / "dataproduct.yaml").read_text(encoding="utf-8"))
    contract = yaml.safe_load((out / "contract.yaml").read_text(encoding="utf-8"))
    policy = yaml.safe_load((out / "policy.yaml").read_text(encoding="utf-8"))
    assert product["owner"]["name"] == "TODO"
    assert contract["schema"][0]["name"] == "customer_id"
    assert policy["allowed_purposes"] == ["TODO"]
    assert "TODO" in policy["access_notes"]
