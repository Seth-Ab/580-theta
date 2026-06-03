# Market Demo Aggregation QC v0

## Inputs

- `outputs/entity_market_labels_v0.csv`: 119 rows
- `outputs/entity_market_exposure_v0.csv`: 58 rows
- `outputs/entities_v0.csv`: 4715 rows
- `outputs/market_definitions_v0.csv`: 7 rows
- `GSE580_theta_data.csv`: 4715 rows

## Compile Step

- Rows excluded as `OUT_OF_SCOPE_CURRENT_MARKETS`: 0
- Compiled panel row count: 119
- Rows with exposure from exposure file: 43
- Rows defaulted to `exposure_weight = 1.0`: 76
- Missing revenue values in panel: 0
- Panel rows with any missing revenue value: 0
- Panel rows with missing market name: 0
- Panel rows with missing exposure weight after defaulting: 0

## Market Row Counts

- `MKT0001`: 14 company-market rows
- `MKT0002`: 19 company-market rows
- `MKT0003`: 13 company-market rows
- `MKT0004`: 13 company-market rows
- `MKT0005`: 17 company-market rows
- `MKT0006`: 12 company-market rows
- `MKT0007`: 31 company-market rows

## Growth Denominator Issues

- None.

## Limitations

- This is a proof-of-concept aggregation, not a full market-coverage system.
- Market totals only cover companies assigned in the v0 label file.
- Default exposure weights are used where Task 4 did not provide explicit exposure rows.
- Growth rates are simple quarter-to-quarter changes using `(new - old) / abs(old)`.
