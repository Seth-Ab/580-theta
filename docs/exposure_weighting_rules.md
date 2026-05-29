# Exposure Weighting Rules

## Purpose

Task 4 estimates how much each diversified company belongs to each Theta market after Task 3 has assigned companies to markets and value-chain roles. The exposure file is intentionally a rough v0 proof of concept, but it must be internally consistent, joinable, and tied to the merged Task 3 output.

## Output

The Task 4 output is `outputs/entity_market_exposure_v0.csv` with these required columns:

`exposure_id, entity_id, ticker, market_id, submarket, exposure_type, exposure_weight, weight_basis, source, as_of_date, confidence_score, notes`

## Starting Point

The exposure layer starts from `outputs/entity_market_labels_v0.csv`.

For v0, rows are created for companies with more than one Task 3 market assignment. The current merged Task 3 file identifies these multi-market groups:

- semiconductor equipment companies assigned to both `MKT0001` Memory Semiconductors and `MKT0002` Semiconductor Manufacturing Equipment
- steel producers or distributors assigned to both `MKT0005` Flat-Rolled Steel and `MKT0006` Rebar and Structural Steel

Do not add companies that are not in Task 3 unless the row is explicitly needed for a documented balancing case.

## Weighting Approach

For each covered ticker, exposure weights must sum to `1.0` across the company's Task 3 assigned markets, unless an exception is documented in `notes`.

Use the best available evidence in this order:

1. reported segment revenue or product mix
2. company business-description evidence from `outputs/company_text_v0.csv` or `data/GSE580_theta_data.csv`
3. Task 3 assignment notes and value-chain role evidence from `outputs/entity_market_labels_v0.csv`
4. conservative analyst estimate when exact segment data is unavailable

Because the available v0 evidence is mostly text-based rather than precise segment revenue, weights are rounded conservative estimates rather than exact measurements.

## Exposure Types

Use these values in `exposure_type`:

- `task3_multi_market_estimate`: company has multiple Task 3 market assignments and the split is estimated from product mix, role, and assignment notes
- `balancing_sentinel`: optional row used only when a company has material activity outside the formal Theta market list and the file needs to preserve a 1.0 company total

The current v0 file does not use a balancing row because all covered companies are weighted across their actual Task 3 markets.

## OUT_OF_SCOPE_CURRENT_MARKETS

`OUT_OF_SCOPE_CURRENT_MARKETS` is a balancing sentinel, not a formal Theta market. It should only be used when a company has material activity outside the current Task 3 market assignments and the row is necessary to make company weights sum to `1.0` without pretending that out-of-scope activity belongs to a defined Theta market.

If this sentinel is used later, validation should allow it as the only non-`MKT` market ID. It should not be joined to `outputs/market_definitions_v0.csv` or treated as a market in market-summary reporting.

## Confidence Scores

Use text confidence labels:

- `high`: strong text or segment evidence and a clear market split
- `medium`: clear multi-market exposure but the numeric split requires judgment
- `low`: rough estimate with limited evidence or unresolved ambiguity

Most v0 rows are `medium` because the merged Task 3 file provides strong assignment evidence but not exact revenue percentages.

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

## Required Validation

Before committing, validate that:

1. every `entity_id` exists in `outputs/entities_v0.csv`
2. every non-balancing `market_id` exists in `outputs/market_definitions_v0.csv`
3. exposure weights sum to `1.0` for each ticker
4. there are no duplicate `(ticker, market_id)` rows
5. all multi-market companies from `outputs/entity_market_labels_v0.csv` are covered
6. `git diff --check` passes

## Current Limitations

`outputs/company_text_v0.csv` and `data/GSE580_theta_data.csv` are cited because Task 3 used them as company-level evidence, but those files were not present in the local Git working tree during this revision. The v0 weights therefore rely directly on the merged Task 3 notes, which already summarize the company-level evidence from those files.
