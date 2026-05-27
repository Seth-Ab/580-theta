# Value-Chain Rules v0

## Purpose

`outputs/market_value_chain_v0.csv` maps the upstream, focal, downstream, substitute, and policy roles around each v0 target market. The file is designed to help later company assignment work use consistent role categories and relationship logic.

This is a role-level map only. It does not assign individual companies, estimate exposure weights, or create market-level signal outputs.

## Input Markets

The v0 value-chain map uses the seven markets defined in `outputs/market_definitions_v0.csv`:

1. `MKT0001` - Memory Semiconductors
2. `MKT0002` - Semiconductor Manufacturing Equipment
3. `MKT0003` - Container Shipping
4. `MKT0004` - Tire Manufacturing
5. `MKT0005` - Flat-Rolled Steel
6. `MKT0006` - Rebar and Structural Steel
7. `MKT0007` - Oil and Gas Exploration and Production

## Output File

- `outputs/market_value_chain_v0.csv`

## Required Columns

- `value_chain_link_id`: Stable v0 relationship identifier using the format `VCL0001`, `VCL0002`, and so on.
- `market_id`: Market identifier from `outputs/market_definitions_v0.csv`.
- `role_category`: Standard role category for the row.
- `role_description`: Plain-language description of the role in this market.
- `direction`: Position relative to the focal market role. Use `focal`, `upstream`, `downstream`, `policy`, or `substitute`.
- `related_role_category`: Role category on the other side of the relationship.
- `relationship_type`: Standard relationship type such as `defines_market`, `supplies_input_to`, `buys_from`, `regulates`, or `substitutes_for`.
- `relationship_description`: Plain-language description of how the roles relate.
- `source`: Evidence or project source used to define the relationship.
- `as_of_date`: Snapshot date for the v0 relationship.
- `confidence_score`: Conservative confidence score for relationship clarity and usefulness.
- `notes`: Short ambiguity flags or later-task guidance.

## Standard Role Categories

- `raw_material_supplier`: Supplies basic commodities or feedstocks used by the focal role.
- `component_supplier`: Supplies specialized parts, materials, or intermediate components.
- `equipment_provider`: Supplies capital equipment or tools used by the focal role.
- `service_provider`: Supplies specialized services needed by the focal role.
- `producer`: Produces raw commodities or industrial output.
- `manufacturer`: Produces finished or intermediate manufactured products.
- `transport_operator`: Operates freight, shipping, or logistics capacity.
- `distributor`: Moves or resells product between producers and end customers.
- `enterprise_customer`: Business, government, or institutional customer.
- `consumer_end_market`: Household or consumer demand channel.
- `regulator_or_policy_body`: Sets policy, safety, trade, environmental, or market-access rules.
- `substitute_provider`: Provides economically relevant substitute products or services.

## Direction Rules

Use `focal` for the core role that defines the market. Use `upstream` for input, equipment, service, and capital-good roles that support the focal role. Use `downstream` for customer, distributor, and demand roles that buy from or depend on the focal role. Use `policy` only when regulation or public policy materially shapes market economics. Use `substitute` for roles that compete with or cap demand for the focal market.

## Standard Relationship Types

- `defines_market`: Identifies the focal role that defines the market.
- `supplies_input_to`: Provides physical inputs, components, capital equipment, infrastructure, or other operating inputs to another role.
- `supplies_service_to`: Provides specialized services, support, or operating capabilities to another role.
- `distributes_for`: Moves, intermediates, processes, resells, or channels output from another role.
- `buys_from`: Purchases output from another role as a customer or end market.
- `regulates`: Sets policy, standards, market access, environmental, trade, safety, or fiscal rules affecting another role.
- `substitutes_for`: Provides an economic alternative that can replace, reduce, or cap demand for another role.

## Relationship Rules

The map should be detailed enough for Task 3 to assign companies into consistent value-chain roles, but it should not become a full supply-chain graph. Rows should describe role categories, not individual companies.

For diversified companies, Task 3 may assign multiple role rows if justified by company text. Task 4 will handle exposure weights later.

## Known Limitations

The v0 file simplifies some markets with complex structures. Semiconductor markets have many process and materials subroles, steel producers may span flat and long products, and integrated oil companies may span upstream, midstream, refining, and marketing. These complexities should be handled through notes in later assignment and exposure files rather than by expanding this v0 map into excessive detail.
