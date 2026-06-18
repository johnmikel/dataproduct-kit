# From CSV

`init from-csv` creates starter manifests from a local CSV file. It is intended
for onboarding an existing dataset into a data-product repo, not for making
production governance claims automatically.

## Command syntax

```bash
dataproduct-kit init from-csv <csv-path> --out <data-product-dir>
```

Example:

```bash
dataproduct-kit init from-csv data/customers.csv --out data-products/customers
```

The command requires a CSV with a header row. It writes the data product
directory, copies the CSV into `data/`, and creates `dataproduct.yaml`,
`contract.yaml`, `semantic.yaml`, and `policy.yaml`.

## What is inferred

- Product and dataset identifiers from the CSV filename.
- A local CSV dataset path and table name.
- Contract schema field names from the header row.
- Basic field types from sample values: boolean, integer, number, timestamp, or
  string.
- A starter `row_count_min` quality check.

## What remains TODO

The scaffold leaves human-owned fields marked as `TODO` where inference would be
unsafe:

- Product domain, description, owner, and support details.
- Field classifications in `contract.yaml`.
- Approved semantic metrics, dimensions, and entities in `semantic.yaml`.
- Allowed purposes, access notes, sensitive fields, and agent or BI constraints
  in `policy.yaml`.
- Freshness policy and stronger quality checks for production use.

## Run doctor

Use `doctor` after scaffolding to see the remaining production gaps:

```bash
dataproduct-kit doctor data-products/customers
dataproduct-kit doctor data-products/customers --profile production --format json
```

`doctor` runs validation, applies the target profile as guidance, and prints
next steps such as adding agent constraints, quality checks, or freshness
metadata.

## Graduate to production

Start with the local `starter` profile:

```bash
dataproduct-kit ci data-products/customers --profile starter
```

Before switching the repository gate to `production`, replace the `TODO` values,
add approved semantic metrics, define freshness and quality expectations, set
`allowed_purposes` to include `agent_context`, document agent constraints, and
map sensitive classifications to `policy.yaml` `sensitive_fields`.

Then run:

```bash
dataproduct-kit doctor data-products/customers --profile production
dataproduct-kit ci data-products/customers --profile production --fail-on warn
```
