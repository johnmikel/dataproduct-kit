from __future__ import annotations

from pathlib import Path

import pytest
from conftest import write_valid_project


def test_agent_context_requires_agent_context_purpose(tmp_path: Path) -> None:
    from dataproduct_kit.context import build_agent_context
    from dataproduct_kit.loader import load_project
    from dataproduct_kit.validators import validate_project

    write_valid_project(tmp_path)
    policy = (tmp_path / "policy.yaml").read_text(encoding="utf-8")
    (tmp_path / "policy.yaml").write_text(
        policy.replace("  - agent_context\n", ""),
        encoding="utf-8",
    )

    project = load_project(tmp_path)

    with pytest.raises(ValueError, match="agent_context"):
        build_agent_context(project, validate_project(project), "churn_rate")


def test_agent_context_rejects_sensitive_dimensions(tmp_path: Path) -> None:
    from dataproduct_kit.context import build_agent_context
    from dataproduct_kit.loader import load_project
    from dataproduct_kit.validators import validate_project

    write_valid_project(tmp_path)
    semantic = (tmp_path / "semantic.yaml").read_text(encoding="utf-8")
    (tmp_path / "semantic.yaml").write_text(
        semantic.replace(
            "dimensions: [plan]",
            "dimensions: [customer_id]",
        ).replace(
            "  - name: plan\n    dataset: subscriptions\n    column: plan\n    type: string\n",
            "  - name: customer_id\n"
            "    dataset: subscriptions\n"
            "    column: customer_id\n"
            "    type: string\n",
        ),
        encoding="utf-8",
    )
    project = load_project(tmp_path)

    with pytest.raises(ValueError, match="sensitive"):
        build_agent_context(project, validate_project(project), "churn_rate")
