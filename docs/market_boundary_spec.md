# Market Boundary Spec v0

## Purpose

`outputs/market_definitions_v0.csv` defines the first target markets for the Team Theta market-definition workflow. The file is intentionally narrow: it establishes practical market boundaries that later tasks can use for value-chain mapping, entity assignment, and diversified exposure weighting.

This v0 pack covers seven markets where broad industry labels can hide meaningful economic differences. It does not try to cover the full company universe.

The v0 markets are based on `TASKS-2.md`, client-provided market-definition examples, and analyst boundary review.

## Scope of Task 1

Task 1 defines market boundaries only. It does not assign companies to markets, map upstream or downstream value-chain roles, or estimate exposure weights.

The v0 target markets are:

1. Memory Semiconductors
2. Semiconductor Manufacturing Equipment
3. Container Shipping
4. Tire Manufacturing
5. Flat-Rolled Steel
6. Rebar and Structural Steel
7. Oil and Gas Exploration and Production

Biotechnology and pharmaceuticals are excluded from this v0 pack because clinical-stage and pre-revenue business models create assignment problems outside the current project scope.

## Decision Support Inputs

`WORK.md` recommends using embedding cluster and nearest-peer outputs as decision support when available. The local root-level `company_clusters_k30.csv` was reviewed as supporting evidence.

Cluster outputs are useful for spotting broad company groupings and mixed clusters, but a cluster is not automatically a market. Task 1 market boundaries remain based on `TASKS-2.md`, client-provided market-definition examples, available project files, and analyst boundary review.

If nearest-peer outputs are unavailable locally, that does not block Task 1, but it should be noted before scaling later tasks.

## Output File

- `outputs/market_definitions_v0.csv`

## Required Columns

- `market_id`: Stable v0 market identifier using the format `MKT0001`, `MKT0002`, and so on.
- `market_name`: Human-readable market name.
- `parent_market_id`: Reserved for future hierarchy. Blank in v0 because each row is treated as a top-level target market.
- `market_level`: Market granularity. Set to `market` for all v0 rows.
- `definition`: Short boundary definition for the market.
- `included_products_services`: Products, services, or activities that should be included when assigning firms later.
- `excluded_products_services`: Products, services, or activities that should not be assigned to the market unless separately justified.
- `substitutes`: Closest substitute products, services, or competing market alternatives.
- `primary_demand_driver`: Main demand driver for the market.
- `geographic_scope`: Practical geographic scope for v0 assignment.
- `source`: Evidence or project source used to define the row.
- `as_of_date`: Snapshot date for the v0 boundary definition.
- `confidence_score`: Conservative confidence score for boundary clarity and assignability.
- `notes`: Short ambiguity flags or future refinement notes.

## Boundary Rules

Market assignment should follow the product or service actually sold, not only the company's broad GICS or sector label. A diversified company can be relevant to more than one market in later tasks, but Task 1 does not assign those exposures.

For manufacturing markets, include firms whose products directly define the market. Exclude upstream raw-material suppliers, general distributors, and end customers unless a later task explicitly assigns them as value-chain participants.

For service markets, include firms providing the core revenue-generating service. Exclude customers, suppliers, equipment vendors, and adjacent transportation or logistics services unless they are separately mapped in Task 2.

## Known Limitations

Some boundaries remain imperfect because several companies operate across adjacent products. Steel producers may sell both flat and long products, semiconductor firms may sell both memory and logic devices, and integrated oil companies may combine upstream, midstream, refining, and marketing operations.

These cases should be flagged in later entity assignment and exposure-weight files rather than forced into a single market.
