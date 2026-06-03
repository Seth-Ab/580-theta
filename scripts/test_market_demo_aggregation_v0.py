#!/usr/bin/env python3

"""Validate Stage 3 Step 1-2 market demo aggregation outputs.

Run from the repository root:

    python scripts/test_market_demo_aggregation_v0.py

The tests are intentionally lightweight and read-only. They verify that the
compiled panel, market weighted revenue, and growth outputs are structurally
correct and internally consistent.
"""

from __future__ import annotations

from pathlib import Path

import pandas as pd


ROOT = Path(__file__).resolve().parents[1]
OUTPUTS = ROOT / "outputs"

PANEL_PATH = OUTPUTS / "market_demo_company_panel_v0.csv"
TIMESERIES_PATH = OUTPUTS / "market_revenue_timeseries_v0.csv"
GROWTH_PATH = OUTPUTS / "market_revenue_growth_v0.csv"
QC_PATH = OUTPUTS / "market_demo_aggregation_qc_v0.md"

CURRENT_MARKETS = {f"MKT000{i}" for i in range(1, 8)}
OUT_OF_SCOPE_MARKET_ID = "OUT_OF_SCOPE_CURRENT_MARKETS"
NUMERIC_TOLERANCE = 1e-6

REV_COLS_ASC = [f"rev_q{i}" for i in range(12)]
REV_COLS_DESC = [f"rev_q{i}" for i in range(11, -1, -1)]

PANEL_COLUMNS = [
    "entity_id",
    "ticker",
    "market_id",
    "market_name",
    "submarket",
    "value_chain_role",
    "assignment_type",
    "relevance_tier",
    "exposure_weight",
    "exposure_type",
    "weight_basis",
    *REV_COLS_ASC,
    "source",
    "as_of_date",
    "confidence_score",
    "notes",
]

TIMESERIES_COLUMNS = [
    "market_id",
    "market_name",
    "company_market_row_count",
    *[f"{col}_weighted" for col in REV_COLS_DESC],
]

GROWTH_COLUMNS = [
    "market_id",
    "market_name",
    "growth_q11_to_q10",
    "growth_q10_to_q9",
    "growth_q9_to_q8",
    "growth_q8_to_q7",
    "growth_q7_to_q6",
    "growth_q6_to_q5",
    "growth_q5_to_q4",
    "growth_q4_to_q3",
    "growth_q3_to_q2",
    "growth_q2_to_q1",
    "growth_q1_to_q0",
]


def assert_equal(actual: object, expected: object, message: str) -> None:
    if actual != expected:
        raise AssertionError(f"{message}: expected {expected!r}, got {actual!r}")


def assert_true(condition: bool, message: str) -> None:
    if not condition:
        raise AssertionError(message)


def assert_close(actual: float, expected: float, message: str) -> None:
    if pd.isna(actual) and pd.isna(expected):
        return
    if pd.isna(actual) or pd.isna(expected) or abs(actual - expected) > NUMERIC_TOLERANCE:
        raise AssertionError(
            f"{message}: expected {expected}, got {actual}, tolerance {NUMERIC_TOLERANCE}"
        )


def print_pass(name: str) -> None:
    print(f"PASS: {name}")


def load_outputs() -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    panel = pd.read_csv(PANEL_PATH)
    timeseries = pd.read_csv(TIMESERIES_PATH)
    growth = pd.read_csv(GROWTH_PATH)
    return panel, timeseries, growth


def test_output_existence() -> None:
    for path in [PANEL_PATH, TIMESERIES_PATH, GROWTH_PATH, QC_PATH]:
        assert_true(path.is_file(), f"Missing expected output file: {path.relative_to(ROOT)}")
    print_pass("output existence")


def test_schemas(
    panel: pd.DataFrame, timeseries: pd.DataFrame, growth: pd.DataFrame
) -> None:
    assert_equal(list(panel.columns), PANEL_COLUMNS, "Panel schema mismatch")
    print_pass("panel schema")

    assert_equal(
        list(timeseries.columns), TIMESERIES_COLUMNS, "Timeseries schema mismatch"
    )
    print_pass("timeseries schema")

    assert_equal(list(growth.columns), GROWTH_COLUMNS, "Growth schema mismatch")
    print_pass("growth schema")


def test_market_coverage(
    panel: pd.DataFrame, timeseries: pd.DataFrame, growth: pd.DataFrame
) -> None:
    for name, df in [
        ("panel", panel),
        ("timeseries", timeseries),
        ("growth", growth),
    ]:
        market_ids = set(df["market_id"].astype(str))
        assert_true(
            market_ids <= CURRENT_MARKETS,
            f"{name} contains market IDs outside current v0 markets: {market_ids - CURRENT_MARKETS}",
        )
        assert_true(
            OUT_OF_SCOPE_MARKET_ID not in market_ids,
            f"{name} contains {OUT_OF_SCOPE_MARKET_ID}",
        )

    assert_equal(
        set(timeseries["market_id"].astype(str)),
        set(growth["market_id"].astype(str)),
        "Timeseries and growth market IDs differ",
    )
    print_pass("market coverage")


def test_exposure_defaults(panel: pd.DataFrame) -> None:
    exposure_weight = pd.to_numeric(panel["exposure_weight"], errors="coerce")
    assert_equal(
        int(exposure_weight.isna().sum()), 0, "Panel has nonnumeric exposure weights"
    )

    default_mask = panel["exposure_type"] == "default_assignment_weight"
    assert_equal(int(default_mask.sum()), 76, "Unexpected default exposure row count")
    assert_true(
        (exposure_weight[default_mask] == 1.0).all(),
        "Defaulted exposure rows do not all have exposure_weight = 1.0",
    )

    non_default_weights = exposure_weight[~default_mask]
    assert_true(
        non_default_weights.notna().all(),
        "Non-default exposure rows have missing exposure weights",
    )
    assert_true(
        (non_default_weights != 1.0).any(),
        "Non-default exposure weights do not appear to preserve explicit fractional weights",
    )
    print_pass("exposure defaults")


def test_weighted_revenue_math(
    panel: pd.DataFrame, timeseries: pd.DataFrame
) -> None:
    panel = panel.copy()
    panel["exposure_weight"] = pd.to_numeric(panel["exposure_weight"], errors="coerce")
    for rev_col in REV_COLS_ASC:
        panel[rev_col] = pd.to_numeric(panel[rev_col], errors="coerce")

    for _, market_row in timeseries.iterrows():
        market_id = market_row["market_id"]
        panel_market = panel[panel["market_id"] == market_id]
        for rev_col in REV_COLS_ASC:
            expected = (panel_market["exposure_weight"] * panel_market[rev_col]).sum()
            actual = market_row[f"{rev_col}_weighted"]
            assert_close(
                float(actual),
                float(expected),
                f"Weighted revenue mismatch for {market_id} {rev_col}",
            )
    print_pass("weighted revenue math")


def test_growth_math(timeseries: pd.DataFrame, growth: pd.DataFrame) -> None:
    denominator_issues: list[str] = []
    growth_by_market = growth.set_index("market_id")

    for _, market_row in timeseries.iterrows():
        market_id = market_row["market_id"]
        growth_row = growth_by_market.loc[market_id]
        for old_q, new_q in zip(range(11, 0, -1), range(10, -1, -1)):
            old_value = market_row[f"rev_q{old_q}_weighted"]
            new_value = market_row[f"rev_q{new_q}_weighted"]
            growth_col = f"growth_q{old_q}_to_q{new_q}"
            actual = growth_row[growth_col]

            if pd.isna(old_value) or old_value == 0 or pd.isna(new_value):
                denominator_issues.append(f"{market_id} {growth_col}")
                assert_true(
                    pd.isna(actual),
                    f"{market_id} {growth_col} should be blank for unusable denominator",
                )
                continue

            expected = (new_value - old_value) / abs(old_value)
            assert_close(
                float(actual),
                float(expected),
                f"Growth mismatch for {market_id} {growth_col}",
            )

    assert_equal(denominator_issues, [], "Unexpected growth denominator issues")
    print_pass("growth math")


def test_join_sanity(panel: pd.DataFrame, timeseries: pd.DataFrame) -> None:
    assert_equal(len(panel), 119, "Unexpected panel row count")
    assert_equal(int(panel["market_name"].isna().sum()), 0, "Missing market_name rows")
    assert_equal(
        int(panel[REV_COLS_ASC].isna().sum().sum()),
        0,
        "Missing revenue values in panel",
    )
    assert_equal(
        int(panel.duplicated(["entity_id", "market_id"]).sum()),
        0,
        "Duplicate entity_id + market_id rows in panel",
    )

    panel_counts = panel.groupby("market_id").size().to_dict()
    for _, row in timeseries.iterrows():
        expected = int(panel_counts[row["market_id"]])
        actual = int(row["company_market_row_count"])
        assert_equal(
            actual,
            expected,
            f"company_market_row_count mismatch for {row['market_id']}",
        )
    print_pass("join sanity")


def test_proof_of_concept_readiness(growth: pd.DataFrame) -> None:
    growth_cols = [col for col in growth.columns if col.startswith("growth_")]
    assert_true(len(growth) >= 7, "Growth output has fewer than seven market rows")
    assert_true(len(growth_cols) >= 11, "Growth output has fewer than 11 growth columns")
    assert_true("growth_q1_to_q0" in growth.columns, "Missing growth_q1_to_q0")
    assert_equal(
        int(growth["growth_q1_to_q0"].isna().sum()),
        0,
        "growth_q1_to_q0 has blank values",
    )
    print_pass("proof-of-concept readiness")
    print(
        "Stage 3 aggregation outputs are ready to feed the simple prediction demo; "
        "this validates pipeline readiness, not predictive accuracy."
    )


def main() -> None:
    print("Running Stage 3 Step 1-2 aggregation tests...")
    test_output_existence()

    panel, timeseries, growth = load_outputs()
    test_schemas(panel, timeseries, growth)
    test_market_coverage(panel, timeseries, growth)
    test_exposure_defaults(panel)
    test_weighted_revenue_math(panel, timeseries)
    test_growth_math(timeseries, growth)
    test_join_sanity(panel, timeseries)
    test_proof_of_concept_readiness(growth)

    print("PASS: all Stage 3 Step 1-2 aggregation tests passed")


if __name__ == "__main__":
    main()
