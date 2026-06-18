# Compatibility Policy

`dataproduct-kit` is still pre-1.0, but early adopters need to know which
surfaces are safe to automate.

## Stable CLI

The stable CLI surface is the command shape used by CI and examples:

- `dataproduct-kit validate <path> --format text|json --fail-on fail|warn`
- `dataproduct-kit ci <path> --format text|json|github --fail-on fail|warn`
- `dataproduct-kit ci <path> --sarif <file>`
- `dataproduct-kit schema dataproduct|contract|semantic|policy|config|all`
- `dataproduct-kit report`, `context`, `export`, and `emit`

Patch releases should not remove commands, rename flags, or change exit-code
meaning. New flags should default to the current behavior.

## Stable Config

The stable config surface is `dataproduct-kit.toml`:

- `[ci].include`
- `[ci].exclude`
- `[ci].fail_on`
- `[ci].profile`
- `[[suppressions]].code`
- `[[suppressions]].path`
- `[[suppressions]].reason`
- `[[suppressions]].expires`

These fields are intended for CI automation and should stay backward-compatible
through the `0.x` line unless a changelog entry calls out a migration.

## Evolving Manifests

The data product manifests are evolving manifests. The current YAML shape is
usable, but the project may still add fields or tighten standards alignment for
ODCS, OSI, and OpenLineage before `1.0`.

When manifest behavior changes, the project should prefer additive fields,
clear finding codes, generated JSON Schema updates, and examples that show the
new recommended shape.
