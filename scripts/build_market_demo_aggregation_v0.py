#!/usr/bin/env python3

"""Build Stage 3 market demo aggregation outputs.

This script implements FINAL-WORK.md Stage 3 Step 1 and Step 2:

1. Compile company-market assignments with revenue and exposure weights.
2. Aggregate weighted revenue to market-level time series.
3. Compute quarter-to-quarter market revenue growth.
4. Write a short QC note documenting row counts and assumptions.
"""

from __future__ import annotations

import csv
from pathlib import Path

import pandas as pd


ROOT = Path(__file__).resolve().parents[1]
OUTPUTS = ROOT / "outputs"

LABELS_PATH = OUTPUTS / "entity_market_labels_v0.csv"
EXPOSURE_PATH = OUTPUTS / "entity_market_exposure_v0.csv"
ENTITIES_PATH = OUTPUTS / "entities_v0.csv"
MARKETS_PATH = OUTPUTS / "market_definitions_v0.csv"
THETA_DATA_PATH = ROOT / "GSE580_theta_data.csv"

PANEL_PATH = OUTPUTS / "market_demo_company_panel_v0.csv"
TIMESERIES_PATH = OUTPUTS / "market_revenue_timeseries_v0.csv"
GROWTH_PATH = OUTPUTS / "market_revenue_growth_v0.csv"
QC_PATH = OUTPUTS / "market_demo_aggregation_qc_v0.md"

OUT_OF_SCOPE_MARKET_ID = "OUT_OF_SCOPE_CURRENT_MARKETS"
DEFAULT_EXPOSURE_TYPE = "default_assignment_weight"
DEFAULT_WEIGHT_BASIS = (
    "no exposure row; assignment treated as full exposure for demo."
)

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


def read_inputs() -> dict[str, pd.DataFrame]:
    def read_csv_loose(path: Path) -> pd.DataFrame:
        """Read CSV, folding unquoted extra commas into the final column.

        Some v0 hand-authored files contain notes with unquoted commas. The
        intended schema is still recoverable because those extra comma-split
        fragments belong to the final notes column.
        """

        with path.open(newline="", encoding="utf-8") as input_file:
            reader = csv.reader(input_file)
            header = next(reader)
            rows = []
            for row in reader:
                if len(row) > len(header):
                    row = [*row[: len(header) - 1], ",".join(row[len(header) - 1 :])]
                elif len(row) < len(header):
                    row = [*row, *([""] * (len(header) - len(row)))]
                rows.append(row)
        return pd.DataFrame(rows, columns=header)

    return {
        "labels": read_csv_loose(LABELS_PATH),
        "exposure": read_csv_loose(EXPOSURE_PATH),
        "entities": read_csv_loose(ENTITIES_PATH),
        "markets": read_csv_loose(MARKETS_PATH),
        "theta": read_csv_loose(THETA_DATA_PATH),
    }


def require_columns(df: pd.DataFrame, path: Path, columns: list[str]) -> None:
    missing = [col for col in columns if col not in df.columns]
    if missing:
        raise ValueError(f"{path} is missing required columns: {', '.join(missing)}")


def validate_inputs(inputs: dict[str, pd.DataFrame]) -> None:
    require_columns(
        inputs["labels"],
        LABELS_PATH,
        [
            "entity_id",
            "ticker",
            "market_id",
            "submarket",
            "value_chain_role",
            "assignment_type",
            "relevance_tier",
            "source",
            "as_of_date",
            "confidence_score",
            "notes",
        ],
    )
    require_columns(
        inputs["exposure"],
        EXPOSURE_PATH,
        ["entity_id", "market_id", "exposure_type", "exposure_weight", "weight_basis"],
    )
    require_columns(inputs["entities"], ENTITIES_PATH, ["entity_id", "ticker"])
    require_columns(inputs["markets"], MARKETS_PATH, ["market_id", "market_name"])
    require_columns(inputs["theta"], THETA_DATA_PATH, ["ticker", *REV_COLS_ASC])


def build_panel(inputs: dict[str, pd.DataFrame]) -> tuple[pd.DataFrame, dict[str, object]]:
    labels = inputs["labels"].copy()
    markets = inputs["markets"][["market_id", "market_name"]].copy()
    theta = inputs["theta"][["ticker", *REV_COLS_ASC]].copy()
    exposure = inputs["exposure"][
        ["entity_id", "market_id", "exposure_type", "exposure_weight", "weight_basis"]
    ].copy()

    input_label_rows = len(labels)
    out_of_scope_rows = int((labels["market_id"] == OUT_OF_SCOPE_MARKET_ID).sum())
    labels = labels[labels["market_id"] != OUT_OF_SCOPE_MARKET_ID].copy()

    panel = labels.merge(markets, on="market_id", how="left", validate="many_to_one")
    panel = panel.merge(theta, on="ticker", how="left", validate="many_to_one")
    panel = panel.merge(
        exposure,
        on=["entity_id", "market_id"],
        how="left",
        validate="one_to_one",
        indicator="exposure_merge_status",
    )

    exposure_from_file = int((panel["exposure_merge_status"] == "both").sum())
    defaulted_exposure = int((panel["exposure_merge_status"] == "left_only").sum())

    default_mask = panel["exposure_merge_status"] == "left_only"
    panel.loc[default_mask, "exposure_weight"] = "1.0"
    panel.loc[default_mask, "exposure_type"] = DEFAULT_EXPOSURE_TYPE
    panel.loc[default_mask, "weight_basis"] = DEFAULT_WEIGHT_BASIS

    for col in REV_COLS_ASC:
        panel[col] = pd.to_numeric(panel[col], errors="coerce")
    panel["exposure_weight"] = pd.to_numeric(panel["exposure_weight"], errors="coerce")

    missing_revenue_cells = int(panel[REV_COLS_ASC].isna().sum().sum())
    rows_with_missing_revenue = int(panel[REV_COLS_ASC].isna().any(axis=1).sum())
    missing_market_name_rows = int(panel["market_name"].isna().sum())
    missing_exposure_weight_rows = int(panel["exposure_weight"].isna().sum())

    panel = panel[PANEL_COLUMNS].sort_values(
        ["market_id", "entity_id", "ticker"], kind="stable"
    )

    qc = {
        "input_label_rows": input_label_rows,
        "out_of_scope_rows": out_of_scope_rows,
        "panel_rows": len(panel),
        "exposure_from_file": exposure_from_file,
        "defaulted_exposure": defaulted_exposure,
        "missing_revenue_cells": missing_revenue_cells,
        "rows_with_missing_revenue": rows_with_missing_revenue,
        "missing_market_name_rows": missing_market_name_rows,
        "missing_exposure_weight_rows": missing_exposure_weight_rows,
    }
    return panel, qc


def build_timeseries(panel: pd.DataFrame) -> tuple[pd.DataFrame, pd.Series]:
    weighted = panel[["market_id", "market_name", *REV_COLS_ASC]].copy()
    for col in REV_COLS_ASC:
        weighted[f"{col}_weighted"] = panel[col] * panel["exposure_weight"]

    grouped = (
        weighted.groupby(["market_id", "market_name"], dropna=False)
        [[f"{col}_weighted" for col in REV_COLS_ASC]]
        .sum(min_count=1)
        .reset_index()
    )

    row_counts = panel.groupby(["market_id", "market_name"], dropna=False).size()
    row_counts = row_counts.rename("company_market_row_count").reset_index()

    timeseries = row_counts.merge(
        grouped, on=["market_id", "market_name"], how="left", validate="one_to_one"
    )
    timeseries = timeseries[TIMESERIES_COLUMNS].sort_values("market_id", kind="stable")
    market_row_counts = panel.groupby("market_id").size().sort_index()
    return timeseries, market_row_counts


def build_growth(timeseries: pd.DataFrame) -> tuple[pd.DataFrame, list[str]]:
    growth = timeseries[["market_id", "market_name"]].copy()
    denominator_issues: list[str] = []

    for old_q, new_q in zip(range(11, 0, -1), range(10, -1, -1)):
        old_col = f"rev_q{old_q}_weighted"
        new_col = f"rev_q{new_q}_weighted"
        growth_col = f"growth_q{old_q}_to_q{new_q}"
        values: list[float | None] = []

        for _, row in timeseries.iterrows():
            denominator = row[old_col]
            numerator_new = row[new_col]
            if pd.isna(denominator) or denominator == 0 or pd.isna(numerator_new):
                values.append(None)
                denominator_issues.append(
                    f"{row['market_id']} {growth_col}: denominator/new value missing or denominator zero"
                )
                continue
            values.append((numerator_new - denominator) / abs(denominator))

        growth[growth_col] = values

    growth = growth[GROWTH_COLUMNS].sort_values("market_id", kind="stable")
    return growth, denominator_issues


def write_qc(
    inputs: dict[str, pd.DataFrame],
    panel_qc: dict[str, object],
    market_row_counts: pd.Series,
    denominator_issues: list[str],
) -> None:
    lines = [
        "# Market Demo Aggregation QC v0",
        "",
        "## Inputs",
        "",
        f"- `outputs/entity_market_labels_v0.csv`: {len(inputs['labels'])} rows",
        f"- `outputs/entity_market_exposure_v0.csv`: {len(inputs['exposure'])} rows",
        f"- `outputs/entities_v0.csv`: {len(inputs['entities'])} rows",
        f"- `outputs/market_definitions_v0.csv`: {len(inputs['markets'])} rows",
        f"- `GSE580_theta_data.csv`: {len(inputs['theta'])} rows",
        "",
        "## Compile Step",
        "",
        f"- Rows excluded as `OUT_OF_SCOPE_CURRENT_MARKETS`: {panel_qc['out_of_scope_rows']}",
        f"- Compiled panel row count: {panel_qc['panel_rows']}",
        f"- Rows with exposure from exposure file: {panel_qc['exposure_from_file']}",
        f"- Rows defaulted to `exposure_weight = 1.0`: {panel_qc['defaulted_exposure']}",
        f"- Missing revenue values in panel: {panel_qc['missing_revenue_cells']}",
        f"- Panel rows with any missing revenue value: {panel_qc['rows_with_missing_revenue']}",
        f"- Panel rows with missing market name: {panel_qc['missing_market_name_rows']}",
        f"- Panel rows with missing exposure weight after defaulting: {panel_qc['missing_exposure_weight_rows']}",
        "",
        "## Market Row Counts",
        "",
    ]

    for market_id, count in market_row_counts.items():
        lines.append(f"- `{market_id}`: {int(count)} company-market rows")

    lines.extend(["", "## Growth Denominator Issues", ""])
    if denominator_issues:
        lines.extend(f"- {issue}" for issue in denominator_issues)
    else:
        lines.append("- None.")

    lines.extend(
        [
            "",
            "## Limitations",
            "",
            "- This is a proof-of-concept aggregation, not a full market-coverage system.",
            "- Market totals only cover companies assigned in the v0 label file.",
            "- Default exposure weights are used where Task 4 did not provide explicit exposure rows.",
            "- Growth rates are simple quarter-to-quarter changes using `(new - old) / abs(old)`.",
        ]
    )

    QC_PATH.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> None:
    inputs = read_inputs()
    validate_inputs(inputs)

    panel, panel_qc = build_panel(inputs)
    timeseries, market_row_counts = build_timeseries(panel)
    growth, denominator_issues = build_growth(timeseries)

    panel.to_csv(PANEL_PATH, index=False)
    timeseries.to_csv(TIMESERIES_PATH, index=False)
    growth.to_csv(GROWTH_PATH, index=False)
    write_qc(inputs, panel_qc, market_row_counts, denominator_issues)

    print(f"Wrote {PANEL_PATH.relative_to(ROOT)} ({len(panel)} rows)")
    print(f"Wrote {TIMESERIES_PATH.relative_to(ROOT)} ({len(timeseries)} rows)")
    print(f"Wrote {GROWTH_PATH.relative_to(ROOT)} ({len(growth)} rows)")
    print(f"Wrote {QC_PATH.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
