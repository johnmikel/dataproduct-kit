# JSON Output Compatibility

`dataproduct-kit` treats these top-level suite fields as stable for v1:

- `status`
- `summary`
- `findings`
- `products`
- `profile`
- `config`

Each `products[*].trust_report.policy` object is also part of the stable v1
automation contract for data-product policy evidence.

Minor releases may add fields. They will not remove or rename these core fields
without a major version.
