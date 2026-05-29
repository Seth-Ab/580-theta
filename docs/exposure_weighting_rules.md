# Exposure Weighting Rules v0

## Purpose

`outputs/entity_market_exposure_v0.csv` estimates how much each covered company belongs to each Theta market after Task 3 has assigned companies to markets and value-chain roles.

This file is a rough v0 proof-of-concept layer. Its purpose is not precise segment accounting. Its purpose is to prevent market-level aggregation from treating diversified firms as pure plays when the Task 3 evidence says they are not.

## Output File

- `outputs/entity_market_exposure_v0.csv`

## Required Columns

- `exposure_id`
- `entity_id`
- `ticker`
- `market_id`
- `submarket`
- `exposure_type`
- `exposure_weight`
- `weight_basis`
- `source`
- `as_of_date`
- `confidence_score`
- `notes`

## Starting Point

The exposure layer starts from `outputs/entity_market_labels_v0.csv`.

For v0, rows are created for:

- companies with more than one Task 3 market assignment
- companies with one Task 3 market assignment where Task 3 notes identify material activity outside the current Theta market list

Do not add companies that are not in Task 3 unless the row is explicitly needed as an `OUT_OF_SCOPE_CURRENT_MARKETS` balancing row for a covered Task 3 company.

## Weighting Approach

For each covered ticker, exposure weights must sum to `1.0` across its Task 4 rows.

Use the best available evidence in this order:

1. reported segment revenue or product mix
2. company business-description evidence from `outputs/company_text_v0.csv` or `data/GSE580_theta_data.csv`
3. Task 3 assignment notes and value-chain role evidence from `outputs/entity_market_labels_v0.csv`
4. conservative analyst estimate when exact segment data is unavailable

Because the available v0 evidence is mostly text-based rather than precise segment revenue, weights are rounded conservative estimates rather than exact measurements.

## Exposure Types

Use these values in `exposure_type`:

- `task3_multi_market_estimate`: company has multiple Task 3 market assignments and the split is estimated from product mix, role, and assignment notes
- `single_market_with_out_of_scope_estimate`: company has one Task 3 market assignment, but Task 3 notes indicate material non-current-market activity
- `balancing_sentinel`: row used to preserve a `1.0` company total when material activity sits outside the formal Theta market list

## OUT_OF_SCOPE_CURRENT_MARKETS

`OUT_OF_SCOPE_CURRENT_MARKETS` is a balancing sentinel, not a formal Theta market. Use it only when a covered company has material activity outside the current Task 3 market assignments and the row is necessary to avoid pretending that out-of-scope activity belongs to a defined Theta market.

Validation should allow `OUT_OF_SCOPE_CURRENT_MARKETS` as the only non-`MKT` market ID. It should not be joined to `outputs/market_definitions_v0.csv` or treated as a market in market-summary reporting.

For prediction proof-of-concept aggregation, exclude sentinel rows from market totals. Their purpose is to make the denominator explicit.

## Confidence Scores

Use a numeric score between `0.50` and `0.95`, matching the Task 3 convention.

- `0.85`-`0.95`: strong segment or product evidence and a clear split
- `0.70`-`0.84`: clear exposure but numeric weight requires judgment
- `0.60`-`0.69`: rough estimate with limited evidence or material ambiguity
- Below `0.60`: avoid including in v0 unless the row is needed as a documented balancing sentinel

Do not use `1.00`.

## Market-Specific Rules Used In V0

For semiconductor equipment companies assigned to both memory semiconductors and semiconductor manufacturing equipment:

- `MKT0002` receives the larger weight because these firms are primarily equipment providers.
- `MKT0001` receives a smaller weight representing memory-fab customer exposure or memory-specific tool demand.
- Packaging or bonding equipment with clearer memory ties may receive a slightly higher `MKT0001` share.

For steel companies assigned to both flat-rolled steel and rebar/structural steel:

- weights follow Task 3 notes about whether flat products, long products, or service-center distribution are dominant.
- producers described as flat-products majority receive higher `MKT0005` weights.
- producers described as long-products majority receive higher `MKT0006` weights.
- service centers with mixed flat and structural/bar distribution receive balanced or slightly flat-weighted estimates.

For diversified single-market companies:

- assign the current Theta market only the portion supported by Task 3 evidence
- assign the remaining material activity to `OUT_OF_SCOPE_CURRENT_MARKETS`
- use lower confidence when Task 3 flags human review or broad integrated operations

## Required Validation

Before committing, validate that:

1. required columns appear exactly once and in the required order
2. every `entity_id` exists in `outputs/entities_v0.csv`
3. every non-balancing `market_id` exists in `outputs/market_definitions_v0.csv`
4. exposure weights sum to `1.0` for each covered ticker
5. there are no duplicate `(ticker, market_id)` rows
6. all multi-market companies from `outputs/entity_market_labels_v0.csv` are covered
7. single-market companies with material out-of-scope activity are either covered or intentionally deferred in notes
8. `git diff --check` passes

## Current Limitations

The v0 weights are estimates based on Task 3 notes and available project text evidence. They are good enough to demonstrate weighted market aggregation, but they should not be presented as audited segment revenue shares.
