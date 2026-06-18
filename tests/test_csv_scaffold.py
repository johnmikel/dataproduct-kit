from __future__ import annotations

from pathlib import Path

import pytest
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


def test_scaffold_from_csv_allows_header_only_csv(tmp_path: Path) -> None:
    from dataproduct_kit.csv_scaffold import scaffold_from_csv

    csv_path = tmp_path / "customers.csv"
    csv_path.write_text("customer_id,email\n", encoding="utf-8")
    out = tmp_path / "customers-product"

    scaffold_from_csv(csv_path, out)

    contract = yaml.safe_load((out / "contract.yaml").read_text(encoding="utf-8"))
    assert contract["schema"] == [
        {
            "name": "customer_id",
            "type": "string",
            "nullable": True,
            "classification": "TODO",
        },
        {
            "name": "email",
            "type": "string",
            "nullable": True,
            "classification": "TODO",
        },
    ]


def test_scaffold_from_csv_missing_file_raises_value_error(tmp_path: Path) -> None:
    from dataproduct_kit.csv_scaffold import scaffold_from_csv

    csv_path = tmp_path / "missing.csv"

    with pytest.raises(ValueError) as error:
        scaffold_from_csv(csv_path, tmp_path / "out")
    assert str(error.value) == f"CSV file not found: {csv_path}"


def test_scaffold_from_csv_infers_types_from_first_25_rows(tmp_path: Path) -> None:
    from dataproduct_kit.csv_scaffold import scaffold_from_csv

    csv_path = tmp_path / "measurements.csv"
    rows = ["measurement_id"] + [str(value) for value in range(25)] + ["not-an-integer"]
    csv_path.write_text("\n".join(rows) + "\n", encoding="utf-8")
    out = tmp_path / "measurements-product"

    scaffold_from_csv(csv_path, out)

    contract = yaml.safe_load((out / "contract.yaml").read_text(encoding="utf-8"))
    assert contract["schema"][0]["type"] == "integer"
