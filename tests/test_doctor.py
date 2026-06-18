from __future__ import annotations

from pathlib import Path

from conftest import write_valid_project


def test_doctor_reports_production_gaps(tmp_path: Path) -> None:
    from dataproduct_kit.doctor import inspect_project

    write_valid_project(tmp_path)
    policy = (tmp_path / "policy.yaml").read_text(encoding="utf-8")
    (tmp_path / "policy.yaml").write_text(
        policy.replace(
            "agent_constraints:\n"
            "  - Agents may use the approved churn_rate metric only.\n"
            "  - Agents must include freshness and quality status with answers.\n",
            "agent_constraints: []\n",
        ),
        encoding="utf-8",
    )

    result = inspect_project(tmp_path)

    assert result["status"] == "warn"
    assert result["profile"] == "production"
    assert any("agent_constraints" in item for item in result["next_steps"])
