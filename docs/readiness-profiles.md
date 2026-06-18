# Readiness Profiles

Readiness profiles let teams use the same validator at different adoption
stages. The core contract, quality, freshness, semantic, and policy checks still
run in every profile; the profile adds expectations for how complete the
metadata must be before agent-facing use.

Use `--profile` with CI:

```bash
dataproduct-kit ci data-products --profile starter
dataproduct-kit ci data-products --profile production --fail-on warn
dataproduct-kit ci data-products --profile regulated --fail-on warn
```

Repository defaults can live in `dataproduct-kit.toml`:

```toml
[ci]
profile = "production"
fail_on = "warn"
```

## Profile behavior

`starter` is for local onboarding and first manifests. It reports missing
`agent_constraints`, `quality_checks`, and semantic metrics as warnings, so a
team can see production gaps without blocking early iteration.

`production` is the recommended GitHub Action profile for real pull request
gates. It turns the starter profile gaps into errors and also requires policy
`allowed_purposes`, the `agent_context` purpose, and policy coverage for fields
classified as sensitive.

`regulated` is for teams that need stricter audit evidence. It includes all
`production` rules, requires every contract field to have a classification, and
adds an error when warning-level findings remain unsuppressed.

## Recommendations

Use `starter` on a workstation while creating or importing a data product:

```bash
dataproduct-kit ci data-products/customers --profile starter
```

Use `production` in GitHub Actions:

```yaml
with:
  path: "data-products"
  profile: "production"
  fail-on: "warn"
```

Use `regulated` only when the team can maintain full field classifications and a
warning-free gate. Moving to `regulated` too early usually creates noisy
exceptions instead of better evidence.
