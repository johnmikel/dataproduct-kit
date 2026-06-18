# Publishing

This project is prepared for PyPI Trusted Publishing, but publishing is not
automatic until the matching Trusted Publishers are configured in TestPyPI and
PyPI.

The release workflow is `.github/workflows/publish.yml`. It runs when a GitHub
Release is published, and it can also be started manually with
`workflow_dispatch` for a TestPyPI dry run.

## Trusted Publisher Setup

Configure two Trusted Publishers:

| Index | Environment | Workflow filename | Repository |
| --- | --- | --- | --- |
| TestPyPI | `testpypi` | `publish.yml` | `johnmikel/dataproduct-kit` |
| PyPI | `pypi` | `publish.yml` | `johnmikel/dataproduct-kit` |

The GitHub workflow already uses the publishing shape expected by PyPI:

```yaml
environment: testpypi
permissions:
  id-token: write
```

For the final PyPI publish job, the environment is `pypi`. The TestPyPI job uses
the TestPyPI upload URL:

```yaml
repository-url: https://test.pypi.org/legacy/
```

No PyPI API token should be added to repository secrets, committed to the repo,
or passed to `pypa/gh-action-pypi-publish`. Trusted Publishing uses GitHub OIDC
to mint short-lived upload credentials for the configured workflow identity.

## Manual Targets

The publish workflow has a manual target input:

```yaml
target: testpypi
```

Use `target: testpypi` to build the package and publish only to TestPyPI. The
PyPI job is skipped for this manual target.

Use `target: pypi` only when you intentionally want a manual production publish.
That path runs TestPyPI first, then PyPI.

A published GitHub Release still runs the full release path: build, publish to
TestPyPI, then publish to PyPI.

## GitHub Environments

Create both GitHub environments before the first real release:

- `testpypi`
- `pypi`

For `pypi`, require manual approval from a maintainer. This keeps publishing to
PyPI intentional even though the workflow starts when a GitHub Release is
published.

## TestPyPI Dry Run

Use this sequence before publishing to PyPI for the first time:

1. Configure the `testpypi` Trusted Publisher in TestPyPI.
2. Create the `testpypi` GitHub environment.
3. In GitHub Actions, run the `Publish` workflow manually with
   `target: testpypi`.
4. Confirm the `publish-testpypi` job uploads `dataproduct-kit` to TestPyPI and
   the `publish-pypi` job is skipped.
5. Install from TestPyPI in a clean environment and run a smoke command:

```bash
python3 -m venv /tmp/dataproduct-kit-testpypi
/tmp/dataproduct-kit-testpypi/bin/python -m pip install \
  --index-url https://test.pypi.org/simple/ \
  --extra-index-url https://pypi.org/simple/ \
  dataproduct-kit==0.4.0
/tmp/dataproduct-kit-testpypi/bin/dataproduct-kit --help
```

After the TestPyPI dry run succeeds, configure the `pypi` Trusted Publisher.
The production publish should normally happen from the GitHub Release path, with
the `pypi` environment approval providing the final manual gate.

## Troubleshooting

If the publish job fails with `invalid-publisher`, check that PyPI or TestPyPI
matches all of these values exactly:

- Repository owner: `johnmikel`
- Repository name: `dataproduct-kit`
- Workflow filename: `publish.yml`
- Environment: `testpypi` or `pypi`

Relevant upstream references:

- PyPI Trusted Publishers: https://docs.pypi.org/trusted-publishers/
- PyPI publishing with Trusted Publishers:
  https://docs.pypi.org/trusted-publishers/using-a-publisher/
- PyPA publish action:
  https://github.com/pypa/gh-action-pypi-publish
