#!/usr/bin/env python3

"""Validate Stage 3 prediction demo outputs.

The test is read-only with respect to validation, but it first regenerates the
Stage 3 aggregation and prediction outputs to prove the workflow is
reproducible from the current scripts and local private data.
"""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

import pandas as pd


ROOT = Path(__file__).resolve().parents[1]
OUTPUTS = ROOT / "outputs"

AGGREGATION_SCRIPT = ROOT / "scripts" / "build_market_demo_aggregation_v0.py"
PREDICTION_SCRIPT = ROOT / "scripts" / "build_market_prediction_demo_v0.py"
PREDICTION_PATH = OUTPUTS / "market_prediction_demo_v0.csv"
NOTES_PATH = OUTPUTS / "market_prediction_demo_notes_v0.md"

OUT_OF_SCOPE_MARKET_ID = "OUT_OF_SCOPE_CURRENT_MARKETS"
TOLERANCE = 1e-10

PREDICTION_COLUMNS = [
    "market_id",
    "market_name",
    "actual_growth_q1_to_q0",
    "predicted_growth_q1_to_q0",
    "prediction_error",
    "abs_prediction_error",
    "baseline_predicted_growth_q1_to_q0",
    "baseline_prediction_error",
    "baseline_abs_prediction_error",
    "prior_growth_mean",
    "latest_prior_growth",
    "model_type",
    "notes",
]


def assert_equal(actual: object, expected: object, message: str) -> None:
    if actual != expected:
        raise AssertionError(f"{message}: expected {expected!r}, got {actual!r}")


def assert_true(condition: bool, message: str) -> None:
    if not condition:
        raise AssertionError(message)


def assert_close(actual: float, expected: float, message: str) -> None:
    if pd.isna(actual) or pd.isna(expected) or abs(actual - expected) > TOLERANCE:
        raise AssertionError(f"{message}: expected {expected}, got {actual}")


def run_script(script: Path) -> None:
    result = subprocess.run(
        [sys.executable, str(script)],
        cwd=ROOT,
        check=True,
        capture_output=True,
        text=True,
    )
    print(result.stdout.strip())


def print_pass(name: str) -> None:
    print(f"PASS: {name}")


def test_output_existence() -> None:
    assert_true(PREDICTION_PATH.is_file(), "Missing outputs/market_prediction_demo_v0.csv")
    assert_true(
        NOTES_PATH.is_file(), "Missing outputs/market_prediction_demo_notes_v0.md"
    )
    print_pass("prediction output existence")


def test_prediction_schema_and_rows(predictions: pd.DataFrame) -> None:
    assert_equal(list(predictions.columns), PREDICTION_COLUMNS, "Prediction schema mismatch")
    assert_equal(len(predictions), 7, "Prediction output should have seven rows")
    assert_true(
        OUT_OF_SCOPE_MARKET_ID not in set(predictions["market_id"].astype(str)),
        "Prediction output contains OUT_OF_SCOPE_CURRENT_MARKETS",
    )
    print_pass("prediction schema and rows")


def test_prediction_values(predictions: pd.DataFrame) -> None:
    numeric_cols = [
        "actual_growth_q1_to_q0",
        "predicted_growth_q1_to_q0",
        "prediction_error",
        "abs_prediction_error",
        "baseline_predicted_growth_q1_to_q0",
        "baseline_prediction_error",
        "baseline_abs_prediction_error",
    ]
    for col in numeric_cols:
        predictions[col] = pd.to_numeric(predictions[col], errors="coerce")
        assert_equal(int(predictions[col].isna().sum()), 0, f"{col} has blank values")

    for _, row in predictions.iterrows():
        prediction_error = (
            row["actual_growth_q1_to_q0"] - row["predicted_growth_q1_to_q0"]
        )
        assert_close(
            row["prediction_error"],
            prediction_error,
            f"prediction_error mismatch for {row['market_id']}",
        )
        assert_close(
            row["abs_prediction_error"],
            abs(prediction_error),
            f"abs_prediction_error mismatch for {row['market_id']}",
        )

        baseline_error = (
            row["actual_growth_q1_to_q0"]
            - row["baseline_predicted_growth_q1_to_q0"]
        )
        assert_close(
            row["baseline_prediction_error"],
            baseline_error,
            f"baseline_prediction_error mismatch for {row['market_id']}",
        )
        assert_close(
            row["baseline_abs_prediction_error"],
            abs(baseline_error),
            f"baseline_abs_prediction_error mismatch for {row['market_id']}",
        )

    print_pass("prediction value math")


def test_notes_language() -> None:
    notes = NOTES_PATH.read_text(encoding="utf-8").lower()
    assert_true(
        "proof-of-concept demo" in notes,
        "Prediction notes must describe this as a proof-of-concept demo",
    )
    assert_true(
        "not a production forecasting model" in notes,
        "Prediction notes must say this is not a production forecasting model",
    )
    print_pass("prediction notes language")


def main() -> None:
    print("Running Stage 3 prediction demo tests...")
    run_script(AGGREGATION_SCRIPT)
    print_pass("aggregation rebuild")
    run_script(PREDICTION_SCRIPT)
    print_pass("prediction rebuild")

    test_output_existence()
    predictions = pd.read_csv(PREDICTION_PATH)
    test_prediction_schema_and_rows(predictions)
    test_prediction_values(predictions)
    test_notes_language()

    print("PASS: all Stage 3 prediction demo tests passed")


if __name__ == "__main__":
    main()
