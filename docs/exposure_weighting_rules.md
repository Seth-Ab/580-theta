# Exposure Weighting Rules

## Purpose

This document explains the v0 approach for estimating how much each company is exposed to Team Theta's target markets. The exposure file supports market-level aggregation by allowing diversified firms to contribute partially to a market instead of forcing every company into a single label.

## Output

The Task 4 output is `outputs/entity_market_exposure_v0.csv` with these columns:

`exposure_id, entity_id, ticker, market_id, submarket, exposure_type, exposure_weight, weight_basis, source, as_of_date, confidence_score, notes`

## Weighting Approach

Each row is one company-market exposure. For focused companies, the exposure weight is usually `1.0`. For diversified companies, the market exposure is estimated conservatively and the remaining business is assigned to `OUT_OF_SCOPE_CURRENT_MARKETS` when the other activity does not fit the current market list.

Weights should sum to `1.0` for each ticker across all exposure rows. This makes the file usable for weighted aggregation without overstating diversified firms.

## Evidence Hierarchy

Use the strongest available basis:

1. Reported segment revenue or product revenue mix
2. Clear company segment or product mix descriptions
3. Value-chain role evidence from the market map
4. Conservative analyst estimate when exact mix is unavailable

## Confidence Scores

Use text confidence labels:

- `high`: company is mostly a focused participant in the market or has clear segment evidence
- `medium`: company has clear exposure but the exact split requires judgment
- `low`: exposure is plausible but weakly quantified or should be reviewed later

## V0 Rules Used Here

- Memory semiconductor manufacturers such as `MU` and `SNDK` are treated as high-confidence focal exposure to `MKT0001`.
- Storage hardware firms with memory-related activity, such as `WDC`, receive only partial memory exposure because assembled storage systems are excluded from the market definition.
- Semiconductor tool makers such as `AMAT`, `ASML`, `KLAC`, and `LRCX` are treated as high-confidence exposure to `MKT0002`.
- Container shipping rows focus on liner operators and vessel/container shipping firms. Mixed logistics firms receive partial exposure.
- Upstream oil and gas producers receive high exposure to `MKT0007`; integrated majors receive partial E&P exposure with the rest assigned out of scope.

## Review Notes

This starter file should be reconciled against Task 3 company-market assignments once those assignments are final. Any market IDs not in `market_definitions_v0.csv`, especially `OUT_OF_SCOPE_CURRENT_MARKETS`, are balancing rows rather than formal Theta markets.
