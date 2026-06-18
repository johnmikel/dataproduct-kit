# Finding Codes

Finding codes are stable machine-readable identifiers intended for CI gates,
dashboards, and policy exceptions. Messages may become more specific over time,
but code meanings should remain compatible within the `0.x` release line unless
called out in the changelog.

## Discovery

- `config.invalid`: `dataproduct-kit.toml` could not be parsed or did not match
  the supported config shape.
- `discovery.no_products`: no `dataproduct.yaml` files were found below the path
  passed to `dataproduct-kit ci`.
- `suppression.expired`: a configured suppression is past its expiry date.
- `suppression.unknown_code`: a configured suppression references an unknown
  finding code.
- `suppression.unused`: an active suppression did not match any current finding
  and should be reviewed for removal.

## Manifest Loading

- `manifest.load_error`: a manifest could not be loaded or parsed.

## Dataset And Contract

- `dataset.missing_file`: a declared local data file does not exist.
- `dataset.read_error`: DuckDB could not read the declared data file.
- `contract.unknown_dataset`: `contract.yaml` references a dataset not declared
  in `dataproduct.yaml`.
- `schema.missing_column`: a required contract column is absent from the data.
- `schema.type_mismatch`: data values cannot cast to the declared contract type.
- `schema.nullable`: a non-nullable contract field contains blank or null values.

## Quality Checks

- `quality.invalid_check`: a quality check is missing required configuration.
- `quality.unknown_column`: a quality check references a column outside the
  contract and dataset.
- `quality.not_null`: a not-null quality check found blank or null values.
- `quality.unique`: a uniqueness check found duplicate values.
- `quality.accepted_values`: a value was outside the accepted set.
- `quality.min`: a numeric value was below the configured minimum.
- `quality.max`: a numeric value was above the configured maximum.
- `quality.row_count_min`: the dataset has fewer rows than required.
- `quality.expression`: a custom expression check failed or could not run.

## Freshness

- `freshness.missing`: a dataset does not define a freshness policy.
- `freshness.unknown_column`: a freshness policy references an undeclared column.
- `freshness.no_values`: a freshness timestamp column has no usable values.
- `freshness.stale`: the latest timestamp is older than the freshness SLA.

## Semantic Layer

- `semantic.unknown_dataset`: a metric, dimension, or entity references an
  undeclared dataset.
- `semantic.unknown_column`: a dimension references an undeclared column.
- `semantic.unknown_key`: an entity references an undeclared key.
- `semantic.unknown_dimension`: a metric references an undeclared dimension.
- `semantic.expression`: a metric expression could not be evaluated by DuckDB.

## Policy

- `policy.allowed_purposes`: `policy.yaml` has no allowed purposes.
- `policy.access_notes`: `policy.yaml` has blank access notes.
- `policy.unknown_sensitive_field`: a sensitive field is not declared in the
  contract.
