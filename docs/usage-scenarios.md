# Usage Scenarios

## Data Product CI Gate

A producer changes a data product contract or sample extract. CI runs:

```bash
dataproduct-kit validate . --format json
```

The merge is blocked when schema drift, stale data, broken semantic references,
or policy gaps produce `status: fail`.

## AI-Agent Metric Context

An agent needs context for `churn_rate`. Instead of giving it raw tables or
text-to-SQL access, the platform runs:

```bash
dataproduct-kit context . --metric churn_rate --format json
```

The result contains approved metric definition, freshness, quality status,
policy constraints, and lineage metadata without row-level data.

## BI Semantic Governance

A BI team defines approved metrics in `semantic.yaml`. The validator catches
metrics that reference unknown dimensions or invalid expressions before a
dashboard ships.

## Data Contract Handoff

A producer exports an ODCS-compatible contract for a consumer team:

```bash
dataproduct-kit export odcs . --out contract.json
```

The same folder can emit a trust report proving the current contract and sample
data validated.

## Audit Evidence Pack

A data owner emits JSON/Markdown trust reports and OpenLineage-compatible events
for lightweight governance evidence:

```bash
dataproduct-kit report . --format markdown
dataproduct-kit emit openlineage .
```
