# Publishing

This project is prepared for PyPI Trusted Publishing, but publishing is not
automatic until the matching Trusted Publishers are configured in TestPyPI and
PyPI.

The release workflow is `.github/workflows/publish.yml`. It runs only when a
GitHub Release is published.

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
3. Temporarily keep the `publish-pypi` job blocked by not configuring the `pypi`
   Trusted Publisher yet.
4. Create a GitHub Release for the candidate tag.
5. Confirm the `publish-testpypi` job uploads `dataproduct-kit` to TestPyPI.
6. Install from TestPyPI in a clean environment and run a smoke command:

```bash
python3 -m venv /tmp/dataproduct-kit-testpypi
/tmp/dataproduct-kit-testpypi/bin/python -m pip install \
  --index-url https://test.pypi.org/simple/ \
  --extra-index-url https://pypi.org/simple/ \
  dataproduct-kit==0.4.0
/tmp/dataproduct-kit-testpypi/bin/dataproduct-kit --help
```

After the TestPyPI dry run succeeds, configure the `pypi` Trusted Publisher and
approve the `pypi` environment deployment for the production publish.

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
