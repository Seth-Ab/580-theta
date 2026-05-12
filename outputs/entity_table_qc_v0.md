# Entity Table QC v0

Source files:

- `outputs/entities_v0.csv`
- `GSE580_theta_data.csv`

Generated as of: `2026-05-08`

## Summary

| Check | Result |
| --- | ---: |
| Total rows in `entities_v0.csv` | 4,715 |
| Total rows in `GSE580_theta_data.csv` | 4,715 |
| Duplicate ticker groups | 0 |
| Duplicate ticker rows | 0 |
| Rows using ticker fallback as `company_name` | 4,715 |
| Rows with `country = Unknown` | 4,440 |
| Rows with missing `industry_group` in raw source | 21 |
| Rows with missing `primary_industry` in raw source | 21 |
| Rows with missing `ci_geographic_scope` in raw source | 1,448 |

## Identity Limitations

- `GSE580_theta_data.csv` does not include a true `company_name` column, so every v0 entity row currently uses ticker as the company-name fallback.
- `canonical_name` is therefore also ticker-based in v0, not a cleaned legal company name.
- Legal suffix stripping is not applied to ticker fallbacks. This keeps tickers such as `ACCO` and `COCO` unchanged.
- Parent/subsidiary relationships are intentionally unresolved in v0.
- Country inference is conservative. Most rows remain `Unknown` because the source does not include a dedicated country field and geographic exposure text often describes markets served rather than domicile.
- Industry fields are available in the raw source, but 21 rows are missing `industry_group` and 21 rows are missing `primary_industry`.
- Private and foreign competitors mentioned in text fields are not represented as standalone entities in v0.
- Alias handling, ticker history, corporate actions, and richer legal-name resolution are deferred to the Task 3 alias/entity-resolution layer.
- Task 2 does not infer legal company names from tickers, perform alias expansion, do cross-record matching beyond duplicate ticker checks, or depend on outside APIs.

## Recommendation

Use `entities_v0.csv` as a join backbone for now, but treat it as an ID scaffold rather than a complete identity master. The highest-value v1 improvement is adding a reliable ticker-to-company-name source before downstream alias and taxonomy work depends on human-readable company names.
