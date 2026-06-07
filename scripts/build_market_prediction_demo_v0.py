#!/usr/bin/env python3

"""Build Stage 3 prediction demo outputs.

This script implements FINAL-WORK.md Stage 3 Step 3 and Step 4 as a small
proof-of-concept. It turns market-level growth history into predicted-versus-
actual output for the next observed growth value. The model is intentionally
simple and should not be interpreted as a production forecasting system.
"""

from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd


ROOT = Path(__file__).resolve().parents[1]
OUTPUTS = ROOT / "outputs"

GROWTH_PATH = OUTPUTS / "market_revenue_growth_v0.csv"
PREDICTION_PATH = OUTPUTS / "market_prediction_demo_v0.csv"
NOTES_PATH = OUTPUTS / "market_prediction_demo_notes_v0.md"

FEATURE_GROWTH_COLS = [
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
]
TARGET_COL = "growth_q1_to_q0"
RIDGE_LAMBDA = 1e-6

OUTPUT_COLUMNS = [
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


def require_columns(df: pd.DataFrame, columns: list[str]) -> None:
    missing = [col for col in columns if col not in df.columns]
    if missing:
        raise ValueError(f"{GROWTH_PATH} is missing required columns: {', '.join(missing)}")


def fit_predict_ols_or_ridge(
    x_train: np.ndarray, y_train: np.ndarray, x_test: np.ndarray
) -> tuple[float, str]:
    design_train = np.column_stack([np.ones(len(x_train)), x_train])
    design_test = np.array([1.0, *x_test], dtype=float)
    rank = np.linalg.matrix_rank(design_train)

    if rank == design_train.shape[1]:
        beta, *_ = np.linalg.lstsq(design_train, y_train, rcond=None)
        return float(design_test @ beta), "leave_one_out_ols"

    penalty = RIDGE_LAMBDA * np.eye(design_train.shape[1])
    penalty[0, 0] = 0.0
    beta = np.linalg.solve(design_train.T @ design_train + penalty, design_train.T @ y_train)
    return float(design_test @ beta), "leave_one_out_ridge_fallback"


def build_predictions(growth: pd.DataFrame) -> pd.DataFrame:
    growth = growth.copy()
    for col in [*FEATURE_GROWTH_COLS, TARGET_COL]:
        growth[col] = pd.to_numeric(growth[col], errors="coerce")

    required_values = growth[[*FEATURE_GROWTH_COLS, TARGET_COL]]
    if required_values.isna().any().any():
        missing = required_values.columns[required_values.isna().any()].tolist()
        raise ValueError(f"Prediction demo cannot run with missing growth values: {missing}")

    growth["prior_growth_mean"] = growth[FEATURE_GROWTH_COLS].mean(axis=1)
    growth["latest_prior_growth"] = growth["growth_q2_to_q1"]

    features = growth[["prior_growth_mean", "latest_prior_growth"]].to_numpy(dtype=float)
    target = growth[TARGET_COL].to_numpy(dtype=float)

    predictions: list[float] = []
    model_types: list[str] = []
    for idx in range(len(growth)):
        train_mask = np.ones(len(growth), dtype=bool)
        train_mask[idx] = False
        prediction, model_type = fit_predict_ols_or_ridge(
            features[train_mask], target[train_mask], features[idx]
        )
        predictions.append(prediction)
        model_types.append(model_type)

    output = pd.DataFrame(
        {
            "market_id": growth["market_id"],
            "market_name": growth["market_name"],
            "actual_growth_q1_to_q0": target,
            "predicted_growth_q1_to_q0": predictions,
            "baseline_predicted_growth_q1_to_q0": growth["prior_growth_mean"],
            "prior_growth_mean": growth["prior_growth_mean"],
            "latest_prior_growth": growth["latest_prior_growth"],
            "model_type": model_types,
        }
    )
    output["prediction_error"] = (
        output["actual_growth_q1_to_q0"] - output["predicted_growth_q1_to_q0"]
    )
    output["abs_prediction_error"] = output["prediction_error"].abs()
    output["baseline_prediction_error"] = (
        output["actual_growth_q1_to_q0"]
        - output["baseline_predicted_growth_q1_to_q0"]
    )
    output["baseline_abs_prediction_error"] = output["baseline_prediction_error"].abs()
    output["notes"] = (
        "Leave-one-out proof-of-concept prediction; compare to prior-growth-mean baseline."
    )

    return output[OUTPUT_COLUMNS].sort_values("market_id", kind="stable")


def directional_accuracy(actual: pd.Series, predicted: pd.Series) -> float:
    return float((np.sign(actual) == np.sign(predicted)).mean())


def write_notes(predictions: pd.DataFrame) -> None:
    mae = float(predictions["abs_prediction_error"].mean())
    baseline_mae = float(predictions["baseline_abs_prediction_error"].mean())
    direction = directional_accuracy(
        predictions["actual_growth_q1_to_q0"],
        predictions["predicted_growth_q1_to_q0"],
    )
    baseline_direction = directional_accuracy(
        predictions["actual_growth_q1_to_q0"],
        predictions["baseline_predicted_growth_q1_to_q0"],
    )
    model_types = ", ".join(sorted(predictions["model_type"].unique()))

    lines = [
        "# Market Prediction Demo Notes v0",
        "",
        "## Setup",
        "",
        f"- Input file: `outputs/market_revenue_growth_v0.csv`",
        "- Features used: `prior_growth_mean` and `latest_prior_growth`.",
        "- `prior_growth_mean` is the average of `growth_q11_to_q10` through `growth_q2_to_q1`.",
        "- `latest_prior_growth` is `growth_q2_to_q1`.",
        "- Target: `growth_q1_to_q0`.",
        f"- Model used: {model_types}.",
        "- Baseline: predict `growth_q1_to_q0` using `prior_growth_mean`.",
        "",
        "## Summary Metrics",
        "",
        f"- Mean absolute error: {mae:.6f}",
        f"- Baseline mean absolute error: {baseline_mae:.6f}",
        f"- Directional accuracy: {direction:.3f}",
        f"- Baseline directional accuracy: {baseline_direction:.3f}",
        "",
        "## Interpretation",
        "",
        "This is a tiny proof-of-concept demo with only seven market observations.",
        "It is not a production forecasting model, and accuracy is not the main claim.",
        "The useful result is that the Theta market framework now produces market-level growth features that can feed a transparent predicted-versus-actual workflow.",
        "The baseline comparison provides a simple check on whether the fitted demo adds anything beyond each market's own prior average growth.",
        "These results should be described as pipeline validation rather than evidence of robust predictive performance.",
    ]
    NOTES_PATH.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> None:
    growth = pd.read_csv(GROWTH_PATH)
    require_columns(growth, ["market_id", "market_name", *FEATURE_GROWTH_COLS, TARGET_COL])

    predictions = build_predictions(growth)
    predictions.to_csv(PREDICTION_PATH, index=False)
    write_notes(predictions)

    print(f"Wrote {PREDICTION_PATH.relative_to(ROOT)} ({len(predictions)} rows)")
    print(f"Wrote {NOTES_PATH.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
