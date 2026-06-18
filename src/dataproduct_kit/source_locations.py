from __future__ import annotations

import re
from pathlib import Path

from dataproduct_kit.config import CONFIG_FILENAME
from dataproduct_kit.models import Finding

_QUOTED_TOKEN = re.compile(r"'([^']+)'")

_PROFILE_MANIFEST_BY_CODE = {
    "profile.agent_constraints_missing": "policy.yaml",
    "profile.allowed_purposes_missing": "policy.yaml",
    "profile.agent_purpose_missing": "policy.yaml",
    "profile.sensitive_fields_missing": "policy.yaml",
    "profile.quality_checks_missing": "contract.yaml",
    "profile.classification_missing": "contract.yaml",
    "profile.semantic_metrics_missing": "semantic.yaml",
    "profile.unsuppressed_warning": CONFIG_FILENAME,
}


def manifest_for_code(code: str) -> str:
    if code in _PROFILE_MANIFEST_BY_CODE:
        return _PROFILE_MANIFEST_BY_CODE[code]
    prefix = code.split(".", 1)[0]
    if prefix in {"config", "suppression"}:
        return CONFIG_FILENAME
    if prefix in {"contract", "schema", "quality"}:
        return "contract.yaml"
    if prefix == "semantic":
        return "semantic.yaml"
    if prefix == "policy":
        return "policy.yaml"
    return "dataproduct.yaml"


def with_product_source_lines(
    root: Path,
    product_path: str,
    findings: list[Finding],
) -> list[Finding]:
    product_dir = root if product_path == "." else root / product_path
    return [
        _with_source_line(finding, product_dir / manifest_for_code(finding.code))
        for finding in findings
    ]


def with_config_source_lines(root: Path, findings: list[Finding]) -> list[Finding]:
    return [_with_source_line(finding, root / CONFIG_FILENAME) for finding in findings]


def _with_source_line(finding: Finding, source_path: Path) -> Finding:
    if finding.line is not None:
        return finding
    line = _find_line(source_path, _tokens(finding))
    if line is None:
        return finding
    return finding.model_copy(update={"line": line})


def _tokens(finding: Finding) -> list[str]:
    tokens = [token for token in _QUOTED_TOKEN.findall(finding.message) if token]
    if finding.check:
        tokens.insert(0, finding.check)
    return tokens


def _find_line(source_path: Path, tokens: list[str]) -> int | None:
    if not source_path.exists():
        return None
    lines = source_path.read_text(encoding="utf-8").splitlines()
    for token in tokens:
        for index, line in enumerate(lines, start=1):
            if token in line:
                return index
    return _first_content_line(lines)


def _first_content_line(lines: list[str]) -> int | None:
    for index, line in enumerate(lines, start=1):
        stripped = line.strip()
        if stripped and not stripped.startswith("#"):
            return index
    return None
