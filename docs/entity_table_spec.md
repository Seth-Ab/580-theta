# Entity Table Spec v0

## Purpose

`outputs/entities_v0.csv` is the canonical company backbone for the Team Theta market-definition workflow. It gives each input ticker one stable internal `entity_id` so later outputs can join to a shared company identity layer instead of relying only on raw ticker strings.

## Column Definitions

- `entity_id`: Stable internal identifier for the entity.
- `ticker`: Cleaned public-company ticker, uppercased and stripped of surrounding spaces.
- `company_name`: Company name from the source when available; otherwise the ticker fallback.
- `canonical_name`: Readable cleaned name used for matching and review.
- `parent_entity_id`: Reserved for future parent/subsidiary mapping. Blank in v0.
- `is_public`: `TRUE` for all v0 rows because the source universe is public listed companies.
- `country`: Country from a usable source field or conservative inference; otherwise `Unknown`.
- `region`: Broad region derived from country.
- `source`: Source file used to build the row.
- `as_of_date`: Snapshot date for this v0 output.
- `confidence_score`: Simple quality score for the identity row.
- `notes`: Concise flags for missing names, duplicates, unknown countries, and unresolved parents.

## Cleaning Rules

Tickers are stripped of surrounding whitespace and uppercased. Company names are stripped and repeated spaces are collapsed. `canonical_name` removes common legal suffixes only when they appear at the end of the name, including `Inc`, `Inc.`, `Corp`, `Corporation`, `Ltd`, `PLC`, `LLC`, `Co`, and `Company`.

The v0 cleaner intentionally does not over-clean names. It keeps names readable and avoids removing business descriptors that may matter for analyst review.

## entity_id Rule

Rows are sorted by cleaned ticker. IDs are assigned sequentially in that sorted order using the format `ENT000001`, `ENT000002`, and so on. This makes IDs stable as long as the input ticker universe and sort rule stay fixed.

## confidence_score Rule

- `0.95`: ticker exists and `company_name` exists in the source row.
- `0.80`: ticker exists but `company_name` is missing, so ticker is used as the fallback company name.
- `0.60`: duplicate or ambiguous ticker issues appear.

## Known Limitations of v0

- The current source file may not contain a `company_name` column, so v0 may use ticker fallbacks.
- Parent/subsidiary relationships are not resolved.
- Country inference is conservative and leaves non-obvious cases as `Unknown`.
- Private and foreign competitors named in text fields are not added as separate entities yet.
- Corporate actions, historical ticker changes, and aliases are deferred to the alias/entity-resolution layer.

## Joining Later Tasks

Later task outputs should join to this table through `entity_id`. If an intermediate file only has `ticker`, first join `ticker` to `entities_v0.csv`, then carry `entity_id` into downstream files such as `entity_aliases_v0.csv`, `entity_labels_v0.csv`, embedding inputs, peer-review outputs, and market-level aggregation tables.
