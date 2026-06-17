from __future__ import annotations

import json

from jinja2 import Template

from dataproduct_kit.models import TrustReport

MARKDOWN_TEMPLATE = Template(
    """# Trust Report: {{ report.product_name }}

| Field | Value |
| --- | --- |
| Product ID | {{ report.product_id }} |
| Overall status | {{ report.status }} |
| Checks passed | {{ report.summary.checks_passed }} |
| Checks warned | {{ report.summary.checks_warned }} |
| Checks failed | {{ report.summary.checks_failed }} |

## Freshness
{% for item in report.freshness %}
{% if item.latest_value %}
- {{ item.dataset }}.{{ item.column }}: {{ item.status }}
  latest {{ item.latest_value }}, age {{ item.observed_age_hours }}h
{% else %}
- {{ item.dataset }}.{{ item.column }}: {{ item.status }}
{% endif %}
{% else %}
- No freshness policies defined.
{% endfor %}

## Semantic Metrics
{% for metric in report.semantic.metrics %}
- {{ metric.name }} on {{ metric.dataset }}: `{{ metric.expression }}`
{% else %}
- No metrics defined.
{% endfor %}

## Policy
- Allowed purposes: {{ report.policy.allowed_purposes | join(", ") }}
- Sensitive fields: {{ report.policy.sensitive_fields | join(", ") }}

## Findings
{% for finding in report.findings %}
{% if finding.check %}
- {{ finding.level }} {{ finding.code }} ({{ finding.check }}): {{ finding.message }}
{% else %}
- {{ finding.level }} {{ finding.code }}: {{ finding.message }}
{% endif %}
{% else %}
- No findings.
{% endfor %}
"""
)


def render_json_report(report: TrustReport) -> str:
    return json.dumps(report.model_dump(mode="json"), indent=2, sort_keys=True) + "\n"


def render_markdown_report(report: TrustReport) -> str:
    return MARKDOWN_TEMPLATE.render(report=report).strip() + "\n"
