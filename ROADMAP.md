# Roadmap

`dataproduct-kit` is an alpha project for validating agent-ready data products
from local manifests.

## v0.1 alpha

- Local manifest profile for product, contract, semantic, and policy metadata.
- DuckDB validation over local CSV data.
- Built-in quality checks and freshness checks.
- Trust reports in JSON and Markdown.
- Agent-safe context bundles for approved metrics.
- ODCS-compatible, OSI-inspired, and OpenLineage-compatible outputs.
- Synthetic SaaS churn demo.

## v0.2 standards depth

- Tighten ODCS and OSI compatibility against real-world examples.
- Add schema/version checks for exported standards payloads.
- Add import support for a narrow ODCS subset.
- Add more deterministic golden fixtures for standards output.

## v0.3 ecosystem adapters

- Optional Great Expectations adapter.
- Optional dbt tests and metrics adapter.
- Optional DataHub or OpenMetadata export file generation.

## v0.4 agent and platform integrations

- MCP server only after policy, freshness, and semantic context are stable.
- Warehouse-backed demos for Postgres and one cloud warehouse.
- Catalog sync as an explicit command, not a default runtime dependency.

## Non-goals for v1

- Natural-language querying.
- Text-to-SQL execution.
- Live catalog sync.
- Cloud credentials.
- Agent access to row-level data.
