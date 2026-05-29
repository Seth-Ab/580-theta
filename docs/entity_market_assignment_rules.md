# Entity Market Assignment Rules v0

## Purpose

`outputs/entity_market_labels_v0.csv` assigns entities from `outputs/entities_v0.csv` to the seven v0 markets and value-chain roles defined by Task 1 and Task 2.

This is a conservative first-pass company-to-market assignment layer. It is not a full-universe classifier and it does not estimate exposure weights.

## Inputs Used

Task 1 and Task 2 governing inputs:

- `outputs/market_definitions_v0.csv`
- `outputs/market_value_chain_v0.csv`
- `docs/market_boundary_spec.md`
- `docs/value_chain_rules.md`

Company evidence inputs:

- `outputs/entities_v0.csv`
- `outputs/company_text_v0.csv`
- `outputs/company_peers_top5.csv`
- `outputs/company_clusters_k30.csv`
- `data/GSE580_theta_data.csv`

Cluster output is useful decision support, but a cluster is not truth. It should support text-grounded assignments rather than override company evidence.

## Join Rules

Use `outputs/entities_v0.csv` as the ID backbone.

- Join company evidence to entities by `ticker`.
- Carry the exact `entity_id` and `ticker` from `entities_v0.csv` into the output.
- If a ticker casing mismatch appears, first try exact ticker match, then a conservative case-insensitive match only when it is unique.
- The known `NasdaqGS:ASND` / `NASDAQGS:ASND` casing issue is not assigned in this v0; if it is assigned later, document the case-normalized join in `notes`.
- Do not create assignment rows without an `entity_id`.

## Allowed Markets

Use only these `market_id` values:

- `MKT0001`: Memory Semiconductors
- `MKT0002`: Semiconductor Manufacturing Equipment
- `MKT0003`: Container Shipping
- `MKT0004`: Tire Manufacturing
- `MKT0005`: Flat-Rolled Steel
- `MKT0006`: Rebar and Structural Steel
- `MKT0007`: Oil and Gas Exploration and Production

If a company does not clearly map to one of these seven markets using available repo evidence, do not assign it in v0.

## Allowed Value-Chain Roles

Use only these `value_chain_role` values:

- `raw_material_supplier`
- `component_supplier`
- `equipment_provider`
- `service_provider`
- `producer`
- `manufacturer`
- `transport_operator`
- `distributor`
- `enterprise_customer`
- `consumer_end_market`
- `regulator_or_policy_body`
- `substitute_provider`

Focal roles by market:

- `MKT0001`: `manufacturer`
- `MKT0002`: `equipment_provider`
- `MKT0003`: `transport_operator`
- `MKT0004`: `manufacturer`
- `MKT0005`: `producer`
- `MKT0006`: `producer`
- `MKT0007`: `producer`

## Company Selection Rules

Review a company when one or more of these signals exists:

- Company text directly mentions products or services included in a target market.
- `industry_group` or `primary_industry` is related to one of the seven markets.
- Peer output supports a candidate already grounded in text or industry evidence.
- Task 1 or Task 2 artifacts explicitly reference a ticker in relevant market context.

Do not assign from ticker recognition alone. Do not assign from peer similarity alone if company text does not support the market fit.

## Market Membership Rules

Market membership follows the product or service actually sold, not broad sector labels alone.

Preferred evidence order:

1. Company business text from `data/GSE580_theta_data.csv` or `outputs/company_text_v0.csv`
2. Baseline industry labels from the raw and text tables
3. Peer results from `outputs/company_peers_top5.csv`
4. Explicit ticker-level references in Task 1 or Task 2 artifacts

Peer output is decision support only. It can confirm a candidate but does not override business text.

## Value-Chain Role Rules

Choose `value_chain_role` from `outputs/market_value_chain_v0.csv` based on the company's economic relationship to the target market:

- Focal product or service provider: use the focal role for that market.
- Supplier into the focal role: use the matching upstream role.
- Distributor, channel, or customer of focal output: use the matching downstream role.
- Economic alternative to focal output: use `substitute_provider`.
- Policy body: use `regulator_or_policy_body` only if the policy body is actually present as an entity.

Do not label an upstream supplier as a focal market member.

## Submarket Rules

Fill `submarket` only when available evidence supports a meaningful distinction. Leave it blank otherwise.

Do not use `submarket` to repeat `value_chain_role`, assignment status, or diversification status. Put role detail and mixed-exposure flags in `value_chain_role`, `assignment_type`, and `notes`.

Acceptable examples include:

- Memory: `DRAM`, `NAND`, `HBM`
- Semiconductor equipment: `lithography`, `inspection`, `test`, `deposition`, `etch`
- Container shipping: `feeder`, `intermediate`, `transpacific`, `intra-Asia`
- Tires: `passenger tire`, `truck tire`, `replacement`, `OE`
- Flat-rolled steel: `sheet`, `plate`, `coated steel`
- Rebar and structural steel: `rebar`, `structural`, `merchant bar`
- Oil and gas E&P: `oil-weighted`, `gas-weighted`, `offshore`, `shale`

Do not infer a submarket from ticker alone.

## Assignment Type Rules

Use only these `assignment_type` values:

- `focal_market_member`
- `upstream_participant`
- `downstream_participant`
- `substitute_participant`

Map Task 2 direction to assignment type:

- `focal`: `focal_market_member`
- `upstream`: `upstream_participant`
- `downstream` or `policy`: `downstream_participant`
- `substitute`: `substitute_participant`

## Relevance Tier Rules

Use only these `relevance_tier` values:

- `core`
- `important`
- `peripheral`

Rules:

- `core`: clear focal participant or highly important direct participant in the market
- `important`: materially participates in the market but is not central to defining it
- `peripheral`: touches the market with clear evidence but is not one of the main v0 names

Do not use `peripheral` for weak guesses. If evidence is too weak, skip the row.

## Confidence Score Rules

Use a numeric score between `0.50` and `0.95`.

- `0.90`-`0.95`: company text clearly matches the market and role
- `0.80`-`0.89`: market fit is strong but scope is diversified
- `0.70`-`0.79`: likely fit, but role or exposure is broad or mixed
- `0.60`-`0.69`: plausible but evidence is thin or ambiguous; include only when useful
- Below `0.60`: do not include in v0

Do not assign `1.00`.

## Source Rules

`source` must name specific repo files used as evidence. Do not use vague values such as `manual`.

Examples:

- `outputs/company_text_v0.csv; data/GSE580_theta_data.csv`
- `outputs/company_text_v0.csv; data/GSE580_theta_data.csv; outputs/company_peers_top5.csv`
- `outputs/market_definitions_v0.csv; outputs/market_value_chain_v0.csv; outputs/entities_v0.csv`

## Diversified Companies

A company may have more than one row if available evidence clearly supports multiple target markets or roles.

Rules:

- Use one row per `(entity_id, market_id, value_chain_role)`.
- Explain mixed exposure in `notes`.
- Do not estimate exposure weights in Task 3.

Common v0 examples:

- Semiconductor equipment firms may also be upstream equipment providers to memory manufacturers.
- Steel producers may span both flat and long products.
- Integrated oil companies may combine upstream, midstream, refining, chemicals, and marketing.

## Ambiguous Companies

Handle ambiguous firms conservatively:

- Do not assign from ticker identity alone.
- Do not assign from broad market definitions without a company-level clue.
- Use lower confidence when exposure is mixed or company text is broad.
- Explain ambiguity in `notes`.

Examples to flag:

- Mixed memory and logic semiconductor exposure
- Storage-device companies where memory-component versus finished-storage exposure is not clean
- Container vessel owners that charter ships but are not liner operators
- Steel producers serving both flat and long products
- Integrated oil companies with large downstream operations

## Notes Rules

Each row should state the concrete reason for assignment or the evidence limitation. Tricky rows must not have blank notes.

Good notes:

- `Company text identifies DRAM, NAND, and HBM memory manufacturing`
- `Diversified electronics company; memory segment is clear but non-memory exposure is material`
- `Steel producer spans flat and long products; separate rows preserve market membership without weights`
- `Integrated energy company; upstream production is clear but downstream operations also significant`

## Validation Rules

Before finalizing:

- Required columns appear exactly once and in the required order.
- Every `entity_id` exists in `outputs/entities_v0.csv`.
- Every `market_id` is one of the seven v0 markets.
- Every `value_chain_role` is in the allowed role vocabulary.
- Every `assignment_type` is valid.
- Every `relevance_tier` is valid.
- Every row has `source`, `as_of_date`, `confidence_score`, and `notes`.
- No duplicate `(entity_id, market_id, value_chain_role)` rows exist.
- Focal assignments match the Task 2 focal role for the market.
- No obvious upstream supplier is incorrectly labeled as focal.
- `submarket` does not duplicate role labels such as `integrated`, `freight forwarding`, or `steel service center`.

## Current v0 Coverage Approach

This v0 assigns only companies with explicit support in the available business text, industry labels, and peer table. Focal firms are included first for each market, followed by a small number of clear upstream, downstream, or service participants where useful for cycle analysis.

Coverage is intentionally weaker where the source universe has fewer clear public rows or where roles are structurally ambiguous. Those cases are flagged in `notes` and should be revisited during human review.
