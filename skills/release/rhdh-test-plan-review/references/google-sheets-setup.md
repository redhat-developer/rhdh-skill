# Google Sheets capability

This model-invoked skill detects Google Sheets access; it does not install `gog`, start OAuth, or
repair credentials. Those human setup actions belong exclusively to `/setup-rhdh-skills`.

## Verify

```bash
python scripts/check_gsheets.py
```

Expected output:

```
✓ gog can read the RHDH schedule
```

If the check fails, stop this branch and tell the user which piece is missing — `gog`
itself, Google authentication, or access to the sheet — and that
`/setup-rhdh-skills google-workspace` is the route that repairs it.

Do not reproduce login or installation instructions here. Resume only after the human runs the
setup route and this read-only check succeeds.
