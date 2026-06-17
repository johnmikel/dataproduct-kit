from __future__ import annotations

from pathlib import Path
from textwrap import dedent


def write_text(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(dedent(content).lstrip(), encoding="utf-8")


def write_valid_project(root: Path) -> Path:
    write_text(
        root / "dataproduct.yaml",
        """
        id: saas_churn
        name: SaaS Churn Data Product
        domain: growth
        version: "1.0.0"
        description: Trusted churn metric for customer retention reporting.
        owner:
          name: Growth Analytics
          email: growth-analytics@example.com
          team: Growth
        datasets:
          - id: subscriptions
            path: data/subscriptions.csv
            format: csv
            table: subscriptions
            freshness:
              column: updated_at
              max_age_hours: 48
              reference_time: "2026-06-17T00:00:00Z"
        """,
    )
    write_text(
        root / "contract.yaml",
        """
        version: "0.1"
        dataset: subscriptions
        schema:
          - name: customer_id
            type: string
            nullable: false
            classification: internal
          - name: plan
            type: string
            nullable: false
            classification: public
          - name: status
            type: string
            nullable: false
            classification: internal
          - name: churned
            type: boolean
            nullable: false
            classification: internal
          - name: monthly_recurring_revenue
            type: number
            nullable: false
            classification: confidential
          - name: updated_at
            type: timestamp
            nullable: false
            classification: internal
        quality_checks:
          - name: customer_id_not_null
            type: not_null
            column: customer_id
          - name: customer_id_unique
            type: unique
            column: customer_id
          - name: status_values
            type: accepted_values
            column: status
            values: ["active", "canceled"]
          - name: positive_mrr
            type: min
            column: monthly_recurring_revenue
            value: 0
          - name: enough_rows
            type: row_count_min
            value: 5
        """,
    )
    write_text(
        root / "semantic.yaml",
        """
        metrics:
          - name: churn_rate
            label: Churn Rate
            description: Share of subscriptions that churned during the reporting grain.
            dataset: subscriptions
            expression: "sum(case when churned then 1 else 0 end)::double / nullif(count(*), 0)"
            grain: month
            dimensions: [plan]
        dimensions:
          - name: plan
            dataset: subscriptions
            column: plan
            type: string
        entities:
          - name: customer
            dataset: subscriptions
            key: customer_id
        """,
    )
    write_text(
        root / "policy.yaml",
        """
        allowed_purposes:
          - retention_reporting
          - board_metrics
          - agent_context
        access_notes: Use aggregated churn metrics; do not expose customer-level rows to agents.
        sensitive_fields:
          - customer_id
          - monthly_recurring_revenue
        agent_constraints:
          - Agents may use the approved churn_rate metric only.
          - Agents must include freshness and quality status with answers.
        bi_constraints:
          - BI dashboards must use the semantic churn_rate definition.
        """,
    )
    write_text(
        root / "data/subscriptions.csv",
        """
        customer_id,plan,status,churned,monthly_recurring_revenue,updated_at
        cust_001,pro,active,false,99.0,2026-06-16T09:00:00Z
        cust_002,pro,canceled,true,99.0,2026-06-16T09:30:00Z
        cust_003,business,active,false,299.0,2026-06-16T10:00:00Z
        cust_004,business,canceled,true,299.0,2026-06-16T10:30:00Z
        cust_005,starter,active,false,29.0,2026-06-16T11:00:00Z
        """,
    )
    return root
